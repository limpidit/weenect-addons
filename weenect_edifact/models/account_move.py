
from odoo import models, fields, _
from odoo.exceptions import UserError

import base64

from .invoic_d01b_message import InvoicD01BMessage

class AccountMove(models.Model):
    _inherit = 'account.move'

    edifact_attachment_id = fields.Many2one(comodel_name='ir.attachment', string="Edifact attachment")
        
    def generate_edifact_attachment(self):
        self.ensure_one()
        
        try:
            interchange = self._edifact_invoice_get_interchange()

            if self.partner_id.export_format == 'd01b':
                message = InvoicD01BMessage(self)
                interchange.add_message(message)
            # elif self.partner_id.export_format == 'd96a':
            #     data = self.edifact_invoice_generate_data()
            #     edifact_content = base64.b64encode(data.encode('utf-8'))
            #     attachment = self.env['ir.attachment'].create({
            #         'name': f"Invoice {self.name}.txt",
            #         'type': 'binary',
            #         'datas': edifact_content,
            #         'res_model': 'account.move',
            #         'res_id': self.id,
            #         'mimetype': 'text/plain'
            #     })

            attachment = self.env['ir.attachment'].create({
                'name': f"Invoice {self.name}.txt",
                'type': 'binary',
                'datas': base64.b64encode(interchange.serialize().encode('utf-8')),
                'res_model': 'account.move',
                'res_id': self.id,
                'mimetype': 'application/edi'
            })
        except Exception as e:
            raise UserError(_("Error while generating EDIFACT: %s" % e))
        
        if attachment:
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

        partner_names = [partner.display_name[i:i+35] for i in range(0, len(partner.display_name), 35)]
        
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
        
    # I M'a gonflé l'autre
    # def _get_payment_terms_segment_block(self):
    #     return [
    #         ("PAT", "3"),
    #         ("DTM", ["209", self.invoice_date_due.strftime("%Y%m%d"), "102"]),
    #     ]
        
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
            ])

            if line.discount:
                discount_amount = round(line.quantity * product_price_unit * line.discount / 100, 2)
                lines.extend([
                    ("MOA", ["131", - discount_amount])
                ])
                alc_pcd_moa_segment = [
                    ("ALC", "A", "", "", "1", "DI"),
                    ("PCD", ["3", line.discount]),
                    ("MOA", ["8", discount_amount]),
                ]

            lines.extend([
                ("PRI", ["AAB", product_price_unit, "", "", "", "PCE"]),
            ])

            lines.extend(alc_pcd_moa_segment if line.discount else [])

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

        
   