
from odoo import models, fields, _
from odoo.exceptions import UserError

from logging import getLogger
_logger = getLogger(__name__)

import base64

from .invoic_d01b_message import InvoicD01BMessage
from .invoic_d96a_message import InvoicD96AMessage


class EdifactMessage(models.Model):
    _name = 'edifact.message'
    _description = 'EDIFACT Message'

    name = fields.Char(string='Message Name', required=True)
    message_type = fields.Selection([('d01b', 'Futterhaus'), ('d96a', 'Sagaflor')], string='Message Type', required=True)
    state = fields.Selection([('draft', 'Draft'), ('sent', 'Sent'), ('error', 'Error')], 
        default='draft', string='State', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    
    move_ids = fields.Many2many('account.move', string='Related Moves')

    sender_id = fields.Many2one(comodel_name='res.partner', string='Sender', required=True)
    receiver_id = fields.Many2one(comodel_name='res.partner', string='Receiver', required=True)
    message_content = fields.Text(string='Message Content')

    def cron_send_sagaflor_edifact_attachments(self):
        self.ensure_one()

        _logger.info("Cron job to send EDIFACT attachments started.")
        mail_template = self.env.ref('weenect_edifact.email_template_edi_invoic_sagaflor')

        if not self.message_content:
            self.generate_edifact_content()
    
        attachments = []
        attachment = self.env['ir.attachment'].create({
            'name': f"Message_{self.id}.txt",
            'type': 'binary',
            'datas': self.message_content,
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'application/edi'
        })
        attachments.append(attachment.id)
            
        if attachments:
            mail_template.attachment_ids = [(6, 0, attachments)]
            mail_template.send_mail(self.id, force_send=True)

    def generate_edifact_content(self):
        self.ensure_one()

        interchange = self._edifact_invoice_get_interchange()

        if self.message_type == 'd01b':
            for move in self.move_ids:
                message = InvoicD01BMessage(move)
                interchange.add_message(message)

        elif self.message_type == 'd96a':
            for move in self.move_ids:
                message = InvoicD96AMessage(move)
                interchange.add_message(message)

        else:
            raise UserError(_("The selected export format is not supported."))

        for segment in interchange.segments:
            _logger.info(f"Segment: {segment.tag} - {segment.elements}")
            for elem in segment.elements:
                if not isinstance(elem, (str, list)):
                    _logger.warning(f"Segment element not string or list: {repr(elem)}")

        self.message_content = base64.b64encode(interchange.serialize().encode('utf-8'))

    def send_edifact_message(self):
        for record in self:    
            if not record.message_content:
                record.state = 'error'
                record.error_message = _("Message content is empty. Please generate the message content first.")
                continue

            mail_template = False
            
            if self.message_type == 'd96a': 
                mail_template = self.env.ref('weenect_edifact.email_template_edi_invoic_sagaflor')

            if not mail_template:
                raise UserError(_("Email template for sending EDIFACT messages not found."))

            attachments = []
            attachment = self.env['ir.attachment'].create({
                'name': f"Message_{self.id}.txt",
                'type': 'binary',
                'datas': self.message_content,
                'res_model': 'account.move',
                'res_id': self.id,
                'mimetype': 'application/edi'
            })
            attachments.append(attachment.id)
                
            if attachments:
                mail_template.attachment_ids = [(6, 0, attachments)]
                mail_template.send_mail(self.id, force_send=True)

    def _edifact_invoice_get_interchange(self):
        """
        Generates and returns an EDIFACT interchange object for an invoice message.

        This method retrieves the GLN (Global Location Number) identifiers for both the sender and receiver,
        constructs the required EDIFACT sender and recipient information, sets the syntax identifier,
        and creates an interchange record using the 'base.edifact' model.

        Returns:
            recordset: The created EDIFACT interchange record.
        """
        sender = self.sender_id.id_numbers.filtered(lambda x: x.category_id.code == "gln_id_number")
        receiver = self.receiver_id.id_numbers.filtered(lambda x: x.category_id.code == "gln_id_number")

        sender_edifact = [sender, "14"]
        recipient_edifact = [receiver, "14"]
        syntax_identifier = ["UNOC", "3"]

        return self.env["base.edifact"].create_interchange(
            sender_edifact, recipient_edifact, self.id, syntax_identifier
        )