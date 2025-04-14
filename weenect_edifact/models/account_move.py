
from odoo import models, fields, _
from odoo.exceptions import UserError

from datetime import datetime
import logging
import base64
import re

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    edifact_attachment_id = fields.Many2one(comodel_name='ir.attachment', string="Edifact attachment")
        
    def generate_edifact_attachment(self):
        self.ensure_one()
        
        try:
            data = self.edifact_invoice_generate_data()
        except Exception as e:
            raise UserError(_("Error while generating EDIFACT: %s" % e))
        
        _logger.info(f"Generated edifact invoice for move {self.name}")
        _logger.info(data)
        
        if self.edifact_attachment_id:
            self.edifact_attachment_id.unlink()
        
        edifact_content = base64.b64encode(data.encode('utf-8'))   
        attachment = self.env['ir.attachment'].create({
            'name': f"Invoice {self.name}.txt",
            'type': 'binary',
            'datas': edifact_content,
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'text/plain'
        })
        
        self.edifact_attachment_id = attachment.id
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
        
    def _edifact_invoice_get_interchange(self):
        sender = self.env.company.partner_id.id_numbers.filtered(lambda x: x.category_id.code == "gln_id_number")
        sender.ensure_one()
        if self.partner_id.parent_id:
            recipient_partner = self.partner_id.parent_id
        else:
            recipient_partner = self.partner_id
        recipient = recipient_partner.id_numbers.filtered(lambda x: x.category_id.code == "gln_id_number")
        recipient.ensure_one()
        
        if not sender or not recipient:
            raise UserError(_("Partner is not allowed to use the feature."))
        
        sender_edifact = [sender.name, "14"]
        recipient_edifact = [recipient.name, "14"]
        syntax_identifier = ["UNOC", "3"]

        return self.env["base.edifact"].create_interchange(
            sender_edifact, recipient_edifact, self.id, syntax_identifier
        )
        
    def edifact_invoice_generate_data(self):
        self.ensure_one()
        edifact_model = self.env["base.edifact"]

        lines = []
        interchange = self._edifact_invoice_get_interchange()
        
        header = self._edifact_invoice_get_header()
        product, taxes = self._edifact_invoice_get_product()
        summary = self._edifact_invoice_get_summary(taxes)
        lines += header + product + summary
        lines.append(("UNT", len(lines) + 1, self.id))
        
        for segment in lines:
            interchange.add_segment(edifact_model.create_segment(*segment))
            
        return interchange.serialize()
    
    
    
    
    ################### HEADER ###################
    
    def _edifact_invoice_get_bgm_segment(self):
        move_type_code = {
            "out_invoice": "380",
            "in_invoice": "381"
        }.get(self.move_type, "381")
        return ("BGM", move_type_code, self.name, "9")

    def _edifact_invoice_get_supplier(self):
        return self._get_partner_segment(self.company_id.partner_id, "SU")

    def _edifact_invoice_get_buyer(self):
        return self._get_partner_segment(self.partner_id, "BY")

    def _edifact_invoice_get_delivery_address(self):
        return self._get_partner_segment(self.partner_shipping_id, "DP")
    
    def _get_partner_segment(self, partner, segment_code):
        
        partner_gln = partner.id_numbers.filtered(lambda x: x.category_id.code == "gln_id_number")
        partner_gln.ensure_one()

        partner_names = [partner.name[i:i+35] for i in range(0, len(partner.name), 35)]
        
        return (
            "NAD",
            segment_code,
            [partner_gln.name, "", "9"],
            "",
            partner_names,
            partner.street,
            partner.city,
            "",
            partner.zip,
            partner.country_id.code
        )
        
    def _get_payment_terms_segment_block(self):
        # term_lines = None
        # discount_percentage, discount_days, payment_term_days = 0, 0, 0
        # if self.invoice_payment_term_id:
        #     term_lines = self.invoice_payment_term_id.line_ids
        #     discount_percentage, discount_days, payment_term_days = (
        #         term_lines.discount_percentage,
        #         term_lines.discount_days if len(term_lines) == 1 else 0,
        #         term_lines.days
        #     )
        # if term_lines:
        #     return [
        #         ("CUX", ["2", "EUR", "4"]),
        #         ("PAT", "7", "", ["5", "3", "D", payment_term_days]),
        #         ("PAT", "22", "", ["5", "3", "D", discount_days]),
        #         ("PCD", "12", discount_percentage),
        #     ]

        return [
            ("PAT", "3"),
            ("DTM", ["209", self.invoice_date.strftime("%Y%m%d"), "102"]),
        ]
        
    def _edifact_invoice_get_header(self):
        source_order = self.line_ids.sale_line_ids.order_id
        source_order.ensure_one()
        
        picking = self.env['stock.picking']
        if self.move_type == 'out_invoice':
            picking = source_order.picking_ids.filtered(lambda x: x.state != 'cancel' and x.picking_type_id.code == 'outgoing')
        elif self.move_type == 'out_refund':
            picking = source_order.picking_ids.filtered(lambda x: x.state != 'cancel' and x.picking_type_id.code == 'incoming')
        picking.ensure_one()
        
        buyer = self.partner_id
        delivery_address = self.partner_shipping_id
        
        header = [
            ("UNH", self.id, ["INVOIC", "D", "96A", "UN", "EAN008"]),
            self._edifact_invoice_get_bgm_segment(),
            ("DTM", ["137", self.invoice_date.strftime("%Y%m%d"), "102"]),
            ("DTM", ["35", picking.date_done.date().strftime("%Y%m%d"), "102"]),
            ("FTX", "ZZZ", "", "", "Zentralregulierung über SAGAFLOR AG"),
            ("FTX", "ZZZ", "", "", "Mehrwertsteuerbefreiung, art. 262 ter-l französisches Steuergesetzbuch"),
        ]
        
        # TODO LIMPIDIT : Voir avec Fitzner concnernaut pour les inforamtions suivantes
        
        # if self.tracking_numbers:
        #     header.append(("FTX", "ZZZ", "", "", self.tracking_numbers))
            
        # if self.payment_reference:
        #     payment_ref_text = "Bitte benutzen Sie den folgenden Verwendungszweck für Ihre Zahlung: %s" % self.payment_reference
        #     header.append(("FTX", "ZZZ", "", "", payment_ref_text))
        
        # if self.invoice_payment_term_id.note:
        #     clean_text = re.sub(r'<.*?>', '', self.invoice_payment_term_id.note)
        #     header.append(("FTX", "ZZZ", "", "", clean_text))
            
        # if self.narration:
        #     clean_text = re.sub(r'<.*?>', '', self.narration)
        #     header.append(("FTX", "ZZZ", "", "", clean_text))
        
        # if self.fiscal_position_id:
        #     clean_text = re.sub(r'<.*?>', '', self.fiscal_position_id.note)
        #     header.append(("FTX", "ZZZ", "", "", clean_text))
            
        header.extend([
            ("RFF", ["ON", source_order.name]),
            ("DTM", ["171", source_order.date_order.date().strftime("%Y%m%d"), "102"]),
            ("RFF", ["DQ", picking.name]),
            ("DTM", ["171", picking.date_done.date().strftime("%Y%m%d"), "102"]),
            self._edifact_invoice_get_supplier(),
            ("RFF", ["VA", self.company_id.vat]),
            self._edifact_invoice_get_buyer(),
            ("RFF", ["VA", buyer.vat]),
        ])
        
        if delivery_address != buyer:
            header.extend([
                self._edifact_invoice_get_delivery_address(),
                ("RFF", ["VA", delivery_address.vat]),
            ])

        header.append(("CUX", ["2", "EUR", "4"]))

        if self.invoice_date_due > self.invoice_date:
            header.extend(self._get_payment_terms_segment_block())
        
        return header


    
    ################### PRODUCT ###################
    
    def _edifact_invoice_get_product(self):
        lines = []
        taxes = {}
        number = 0
        
        for line in self.invoice_line_ids.filtered(lambda x: x.product_id):
            number += 1
            product = line.product_id

            line_pdf_description = line.product_id.client_friendly_name + " " + line.name

            libelle_part1 = line_pdf_description[:35]  # Premier segment (max 35 caractères)
            libelle_part2 = line_pdf_description[35:70] if len(line_pdf_description) > 35 else ""  # Deuxième segment (max 35 caractères)
            libelle_segment = ["", "", "", libelle_part1]
            if libelle_part2:
                libelle_segment.append(libelle_part2)

            product_price_unit = round(line.price_unit, 2)
            line_price_subltotal = round(line.price_subtotal, 2)
            
            product_tax = 0
            if line.tax_ids and line.tax_ids.amount_type == "percent":
                product_tax = line.tax_ids.amount
                if product_tax not in taxes:
                    taxes[product_tax] = line_price_subltotal
                else:
                    taxes[product_tax] += line_price_subltotal
                    
            lines.extend([
                ("LIN", number, "", [product.ean_weenect, "EN"]),
                ("PIA", "5", [product.id, "SA", "", "91"]),
                ("IMD", "A", "", libelle_segment),
                ("QTY", ["47", line.quantity, "PCE"]),
                ("MOA", ["203", line_price_subltotal]),
                ("PRI", ["AAB", product_price_unit, "", "", "", "PCE"]),
            ])

            if line.discount:
                discount_amount = round(line.quantity * product_price_unit * line.discount / 100, 2)
                lines.extend([
                    ("ALC", "A", "", "", "1", "DI"),
                    ("PCD", ["3", line.discount]),
                    ("MOA", ["131", discount_amount]),
                ])

            lines.append(("TAX", "7", "VAT", "", "", ["", "", "", round(product_tax, 2)]))
        
        return lines, taxes

    
    
    ################### SUMMARY ###################
    
    def _edifact_invoice_get_summary(self, taxes):
        summary = [
            ("UNS", "S"),
            ("MOA", ["77", round(self.amount_total, 2)]),
            ("MOA", ["79", round(self.amount_untaxed, 2)])
        ]
        
        for product_tax, price_total in taxes.items():
            summary.extend([
                ("TAX", "7", "VAT", "", "", ["", "", "", round(product_tax, 2)]),
                ("MOA", ["125", round(price_total, 2)]),
                ("MOA", ["124", round(price_total * product_tax / 100, 2)])
            ])
            
        return summary

        
   