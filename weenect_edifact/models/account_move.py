
from odoo import models, fields, _
from odoo.exceptions import UserError

from datetime import datetime
import base64


class AccountMove(models.Model):
    _inherit = 'account.move'

    edifact_attachment_id = fields.Many2one(comodel_name='ir.attachment', string="Edifact attachment")
    note = fields.Text(string="Notes")
    
    def generate_futterhaus_edifact_attachment(self):
        partner = "futterhaus"
        self._generate_edifact_attachment(partner)
        
    def generate_sagaflor_edifact_attachment(self):
        partner = "sagaflor"
        self._generate_edifact_attachment(partner)
        
    def _generate_edifact_attachment(self, partner):
        self.ensure_one()
        if partner == "futterhaus":
            data = self.edifact_invoice_generate_data(partner)
        elif partner == "sagaflor":
            data = self.edifact_invoice_generate_data(partner)
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
        
    def edifact_invoice_generate_data(self, partner):
        self.ensure_one()
        edifact_model = self.env["base.edifact"]
        lines = []
        interchange = self._edifact_invoice_get_interchange(partner)

        header = self._edifact_invoice_get_header(partner)
        product, vals = self._edifact_invoice_get_product()
        summary = self._edifact_invoice_get_summary(vals)
        lines += header + product + summary
        for segment in lines:
            interchange.add_segment(edifact_model.create_segment(*segment))
        return interchange.serialize()
    
    def _edifact_invoice_get_interchange(self, partner):
        sender = None
        company_numbers = self.company_id.partner_id.id_numbers
        if company_numbers:
            sender = company_numbers[0]
        
        recipient = None
        if partner == "futterhaus" and self.company_id.futterhaus_edifact_invoiced_partner_id:
            futterhaus_id_numbers = self.company_id.futterhaus_edifact_invoiced_partner_id.id_numbers
            if futterhaus_id_numbers:
                recipient = futterhaus_id_numbers[0]
        if partner == "sagaflor" and self.company_id.sagaflor_edifact_invoiced_partner_id:
            sagaflor_id_numbers = self.company_id.sagaflor_edifact_invoiced_partner_id.id_numbers
            if sagaflor_id_numbers:
                recipient = sagaflor_id_numbers[0]
        if not recipient:
            partner_numbers = self.partner_id.id_numbers
            if partner_numbers:
                recipient = partner_numbers[0]
            
        if not sender or not recipient:
            raise UserError(_("Partner is not allowed to use the feature."))
        
        sender_edifact = [sender.name, "14"]
        recipient_edifact = [recipient.name, "14"]
        syntax_identifier = ["UNOC", "3"]

        return self.env["base.edifact"].create_interchange(
            sender_edifact, recipient_edifact, self.id, syntax_identifier
        )
        
    def _edifact_invoice_get_buyer(self, partner):
        id_number = self.env["res.partner.id_number"]
        
        if partner == 'futterhaus' and self.company_id.futterhaus_edifact_invoiced_partner_id:
            buyer = self.company_id.futterhaus_edifact_invoiced_partner_id
        elif partner == 'sagaflor' and self.company_id.sagaflor_edifact_invoiced_partner_id:
            buyer = self.company_id.sagaflor_edifact_invoiced_partner_id
        else:
            buyer = self.partner_id
            
        buyer_id_number = id_number.search([('partner_id', '=', buyer.id)], limit=1)
        street = self._edifact_invoice_get_address(buyer)

        return [
            # Buyer information
            (
                "NAD",
                "BY",
                [buyer_id_number.name, "", "9"],
                "",
                buyer.commercial_company_name,
                [street, ""],
                buyer.city,
                "",
                buyer.zip,
                buyer.country_id.code,
            ),
            ("RFF", ["VA", buyer.vat])
        ]
        
    def _edifact_invoice_get_supplier(self):
        id_number = self.env["res.partner.id_number"]
        supplier = self.company_id.partner_id
        supplier_id_number = id_number.search([("partner_id", "=", supplier.id)], limit=1)
        street = self._edifact_invoice_get_address(supplier)
        return [
            # Seller information
            (
                "NAD",
                "SU",
                [supplier_id_number.name, "", "9"],
                "",
                supplier.commercial_company_name,
                [street, ""],
                supplier.city,
                "",
                supplier.zip,
                supplier.country_id.code,
            ),
            # VAT registration number
            ("RFF", ["VA", supplier.vat])
        ]

    def _edifact_invoice_get_shipper(self):
        id_number = self.env["res.partner.id_number"]
        shipper = self.partner_shipping_id
        shipper_id_number = id_number.search([("partner_id", "=", shipper.id)], limit=1)
        return [
            # Delivery party Information
            (
                "NAD",
                "DP",
                [shipper_id_number.name, "", "9"],
                "",
                shipper.commercial_company_name,
                [shipper.street, ""],
                shipper.city,
                "",
                shipper.zip,
                shipper.country_id.code,
            ),
            ("RFF", ["VA", shipper.vat]),
        ]
        
    def _edifact_invoice_get_header(self, partner):
        source_orders = self.line_ids.sale_line_ids.order_id
        today = datetime.now().date().strftime("%Y%m%d")
        move_type_code = "380" if self.move_type in ['in_invoice', 'out_invoice'] else "381"

        term_lines = self.invoice_payment_term_id.line_ids
        discount_percentage, discount_days = (
            term_lines.discount_percentage,
            term_lines.discount_days if len(term_lines) == 1 else 0,
        )

        header = [
            ("UNH", self.id, ["INVOIC", "D", "96A", "UN", "EAN008"]),
            # Commercial invoice
            ("BGM", move_type_code, self.name, "9"),
            # Document/message date/time
            ("DTM", ["137", today, "102"]),
            # 35: Delivery date/time, actual
            ("DTM", [
                "35",
                max((
                    picking.date_done.date().strftime("%Y%m%d")
                    for order in source_orders
                    for picking in order.picking_ids
                    if picking.date_done
                ), default=""),
                "102",
            ]),
            
            # Free text
            ("FTX", "ZZZ", "", "", self.note if self.note else ""),
            
            # Payment ref for SAGAFLOR
            ("FTX", "ZZZ", "", "", self.ref if self.ref and partner == "sagaflor" and move_type_code == "381" else ""),
            
            # 35: Delivery date/time, actual
            ("DTM", [
                "171",
                max((
                    picking.date_done.date().strftime("%Y%m%d")
                    for order in source_orders
                    for picking in order.picking_ids
                    if picking.date_done
                ), default=""),
                "102",
            ]),
            # Delivery note number
            ("RFF", [
                "DQ",
                max((
                    picking.name
                    for order in source_orders
                    for picking in order.picking_ids
                    if picking.date_done
                ), default=""),
            ]),
            
            # Reference currency
            ("CUX", ["2", "EUR", "4"]),
            ("PAT", "3"),
            # Terms net due date
            ("DTM", ["209", self.invoice_date_due.strftime('%Y%m%d'), "102"]),
            # Discount terms
            (
                "PAT",
                "22",
                "",
                ["5", "3", "D", discount_days],
            ),
            # Discount percentage
            (
                "PCD",
                "12",
                discount_percentage,
                "13",
            ),
        ]
        header = (
            header[:7]
            + self._edifact_invoice_get_supplier()
            + self._edifact_invoice_get_buyer(partner)
            + self._edifact_invoice_get_shipper()
            + header[7:]
        )
        return header
    
    def _edifact_invoice_get_product(self):
        number = 0
        segments = []
        vals = {}
        tax = {}
        for line in self.line_ids:
            if line.display_type != "product":
                continue
            number += 1
            product_tax = 0
            product = line.product_id
            discount = round(line.price_unit * line.quantity - line.price_subtotal, 2)
            if line.tax_ids and line.tax_ids.amount_type == "percent":
                product_tax = line.tax_ids.amount
                if product_tax not in tax:
                    tax[product_tax] = line.price_total
                else:
                    tax[product_tax] += line.price_total
            product_seg = [
                # Line item number
                ("LIN", number, "", [product.ean_weenect, "EAN"]),
                # Product identification of supplier's article number
                ("PIA", "1", [product.default_code, "SA"]),
                # Item description of product
                (
                    "IMD",
                    "A",
                    ["", "", "", product.name],
                ),
                # Invoiced quantity
                ("QTY", "47", line.quantity, "PCE"),
                # Line item amount
                ("MOA", ["203", line.price_total]),
                # Line item discount
                ("MOA", ["131", discount]),
                # Calculation net
                ("PRI", ["AAB", round(line.price_total / line.quantity, 2)]),
                # Tax information
                ("TAX", "7", "VAT", "", "", ["", "", "", product_tax]),
                
                # Discount information
                ("ALC", "A", "", "", "1", "DI"),
                ("PCD", ["3", line.discount]),
                ("MOA", ["8", discount])
            ]
            segments.extend(product_seg)
        vals["tax"] = tax
        vals["total_line_item"] = number
        return segments, vals
    
    def _edifact_invoice_get_summary(self, vals):
        tax_list = []
        total_line_item = vals["total_line_item"]
        if "tax" in vals:
            for product_tax, price_total in vals["tax"].items():
                # Tax Information
                tax_list.append(
                    ("TAX", "7", "VAT", ["", "", "", product_tax])
                )
                # Taxed amount
                tax_list.append(("MOA", ["79", round(price_total, 2)]))
                # Tax amount
                tax_list.append(("MOA", ["124", round(price_total * product_tax / 100, 2)]))
                # Taxed amount
                tax_list.append(("MOA", ["125", round(price_total, 2)]))
                
        summary = [
            ("UNS", "S"),
            # Total amount
            ("MOA", ["77", self.amount_total]),
            # Total amount
            ("MOA", ["79", self.amount_total]),
            # Tax amount
            ("MOA", ["124", self.amount_tax]),
            # Taxable amount
            ("MOA", ["125", self.amount_untaxed]),
            
            # Segments count
            ("UNT", 25 + 11 * total_line_item + 4 * len(vals["tax"]), self.id),
        ]
        
        summary = summary[:-1] + tax_list + summary[-1:]
        return summary