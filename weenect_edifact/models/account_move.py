
from odoo import models, fields, _
from odoo.exceptions import UserError

from logging import getLogger
_logger = getLogger(__name__)

import base64
import re

from .invoic_d01b_message import InvoicD01BMessage
from .invoic_d96a_message import InvoicD96AMessage

class AccountMove(models.Model):
    _inherit = 'account.move'

    edifact_attachment_id = fields.Many2one(comodel_name='ir.attachment', string="Edifact attachment")
    has_been_sent = fields.Boolean(string="Has been sent", default=False)

    def cron_send_sagaflor_edifact_attachments(self):
        _logger.info("Cron job to send EDIFACT attachments started.")
        mail_template = self.env.ref('weenect_edifact.email_template_edi_invoic_sagaflor')
        attachments = []

        for record in self:
            record._generate_edifact_attachment()
            attachments.append(record.edifact_attachment_id.id)
            
        if attachments:
            mail_template.attachment_ids = [(6, 0, attachments)]
            mail_template.send_mail(self.id, force_send=True)

    def download_edifact_attachment(self):
        self.ensure_one()
        self._generate_edifact_attachment()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.edifact_attachment_id.id}?download=true',
            'target': 'self',
        }
        
    def _generate_edifact_attachment(self):
        self.ensure_one()
        interchange = self._edifact_invoice_get_interchange()

        if self.partner_id.edi_export_format == 'd01b' or (self.partner_id.parent_id and self.partner_id.parent_id.edi_export_format == 'd01b'):
            message = InvoicD01BMessage(self)
            interchange.add_message(message)

        elif self.partner_id.edi_export_format == 'd96a' or (self.partner_id.parent_id and self.partner_id.parent_id.edi_export_format == 'd96a'):
            message = InvoicD96AMessage(self)
            interchange.add_message(message)

        else:
            raise UserError(_("The selected export format is not supported."))

        for segment in message.segments:
            _logger.info(f"Segment: {segment.tag} - {segment.elements}")
            for elem in segment.elements:
                if not isinstance(elem, (str, list)):
                    _logger.warning(f"Segment element not string or list: {repr(elem)}")

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
        