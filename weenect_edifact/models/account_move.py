
from odoo import models, fields, _
from odoo.exceptions import UserError

from datetime import datetime
import base64


class AccountMove(models.Model):
    _inherit = 'account.move'

    edifact_attachment_id = fields.Many2one(comodel_name='ir.attachment', string="Edifact attachment")
    
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

        header = self._edifact_invoice_get_header()
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
        
    def _edifact_invoice_get_header(self):
        source_orders = self.line_ids.sale_line_ids.order_id
        today = datetime.now().date().strftime("%Y%m%d")
        buyer = self.partner_id
        move_type_code = "380" if self.move_type in ['in_invoice', 'out_invoice'] else "381"

        term_lines = self.invoice_payment_term_id.line_ids
        discount_percentage, discount_days = (
            term_lines.discount_percentage,
            term_lines.discount_days if len(term_lines) == 1 else 0,
        )
        

        header = [
            ("UNH", str(self.id), ["INVOIC", "D", "96A", "UN", "EAN008"]),
            # Commercial invoice
            ("BGM", move_type_code, self.payment_reference, "9"),
            # 35: Delivery date/time, actual
            (
                "DTM",
                [
                    "35",
                    max(
                        (
                            picking.date_done.date().strftime("%Y%m%d")
                            for order in source_orders
                            for picking in order.picking_ids
                            if picking.date_done
                        ),
                        default="",
                    ),
                    "102",
                ],
            ),
            # 11: Despatch date and/or time
            (
                "DTM",
                [
                    "11",
                    min(
                        (
                            order.commitment_date.date().strftime("%Y%m%d")
                            for order in source_orders
                            if order.commitment_date
                        ),
                        default="",
                    ),
                    "102",
                ],
            ),
            # Document/message date/time
            ("DTM", ["137", today, "102"]),
            # Delivery note number
            ("RFF", ["DQ", self.id]),
            # Reference date/time
            # TODO: fixed value for now, to be clarified
            ("DTM", ["171", "99991231", "102"]),
            # Reference currency
            ("CUX", ["2", buyer.currency_id.name, "4"]),
            # Rate of exchange
            ("DTM", ["134", today, "102"]),
            ("PAT", "3"),
            # Terms net due date
            ("DTM", ["13", self.invoice_date_due, "102"]),
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
            # Penalty terms
            # ("PAT", "20"),  # TODO: check value this again later
            # Penalty percentage
            # ("PCD", "15", "0"),  # TODO: check value this again later
            # Allowance percentage
            # ("PCD", "1", "0", "13"),  # TODO: check value this again later
            # Allowance or charge amount
            # ("MOA", "8", "0"),  # TODO: check value this again later
        ]
        header = (
            header[:11]
            + self._edifact_invoice_get_buyer()
            + self._edifact_invoice_get_seller()
            + self._edifact_invoice_get_shipper()
            + header[11:]
        )
        return header