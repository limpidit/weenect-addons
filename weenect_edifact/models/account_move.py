
from odoo import models, fields, _
from odoo.exceptions import UserError

from logging import getLogger
_logger = getLogger(__name__)

import base64

from .invoic_d01b_message import InvoicD01BMessage
from .invoic_d96a_message import InvoicD96AMessage

class AccountMove(models.Model):
    _inherit = 'account.move'

    edifact_attachment_id = fields.Many2one(comodel_name='ir.attachment', string="Edifact attachment")
        
    def generate_edifact_attachment(self):
        self.ensure_one()
        interchange = self._edifact_invoice_get_interchange()

        if self.partner_id.export_format == 'd01b':
            message = InvoicD01BMessage(self)
            interchange.add_message(message)

        if self.partner_id.export_format == 'd96a':
            message = InvoicD96AMessage(self)
            interchange.add_message(message)

        for segment in message.segments:
            _logger.info(f"Segment: {segment.tag} - {segment.elements}")

        attachment = self.env['ir.attachment'].create({
            'name': f"Invoice {self.name}.txt",
            'type': 'binary',
            'datas': base64.b64encode(interchange.serialize().encode('utf-8')),
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'application/edi'
        })
        
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
        