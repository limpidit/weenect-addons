
from odoo import models, fields, _
from odoo.exceptions import UserError

from logging import getLogger
_logger = getLogger(__name__)

import base64

from .invoic_d01b_message import InvoicD01BMessage
from .invoic_d96a_message import InvoicD96AMessage


class EdifactMessage(models.Model):
    _name = 'edifact.message'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'EDIFACT Message'

    name = fields.Char(string='Message Name', required=True)
    message_type = fields.Selection([('d01b', 'Futterhaus'), ('d96a', 'Sagaflor')], string='Message Type', required=True)
    state = fields.Selection([('draft', 'Draft'), ('linked', 'Invoices linked'), ('sent', 'Sent'), ('error', 'Error')], 
        default='draft', string='State', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    
    move_ids = fields.Many2many('account.move', string='Related Moves')

    sender_id = fields.Many2one(comodel_name='res.partner.id_number', string='Sender', required=True)
    receiver_id = fields.Many2one(comodel_name='res.partner.id_number', string='Receiver', required=True)
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

    def link_moves(self):
        """
        Links posted account moves that have not been sent yet to the current EDIFACT message.

        This method performs the following steps:
        1. Ensures the method is called on a single record.
        2. Finds all partners whose 'edi_export_format' matches the message's type.
        3. Searches for posted account moves ('account.move') that:
            - Have not been sent yet ('has_been_sent' is False)
            - Belong to the identified partners
        4. Links these moves to the current message and updates the message state to 'linked'.

        Returns:
             None
        """
        self.ensure_one()
        partners = self.env['res.partner'].search([('edi_export_format', '=', self.message_type)])
        to_send_moves = self.env['account.move'].search([('state', '=', 'posted'), ('has_been_sent', '=', False), ('partner_id', 'in', partners.ids)])
        self.write({
            'move_ids': [(6, 0, to_send_moves.ids)],
            'state': 'linked',
        })

    def set_to_draft(self):
        """
        Reset the state of the EDIFACT message to draft.
        """
        self.ensure_one()
        self.write({
            'state': 'draft',
            'error_message': '',
        })

    def generate_edifact_content(self):
        """
        Generates the EDIFACT message content for the current record based on the selected message type.

        This method constructs an EDIFACT interchange using the appropriate message class
        (`InvoicD01BMessage` or `InvoicD96AMessage`) for each move in `self.move_ids`, depending on
        the value of `self.message_type`. The generated messages are added to the interchange, which
        is then serialized and stored in `self.message_content`.

        If an unsupported message type is selected, or if any error occurs during generation,
        the method logs the error, sets the record state to 'error', and stores the error message.

        Additionally, the method logs information about each segment and its elements in the interchange
        for debugging purposes.

        Raises:
            UserError: If the selected export format is not supported.
        """
        self.ensure_one()

        interchange = self._edifact_invoice_get_interchange()

        try:
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

        except Exception as e:
            _logger.error(f"Error generating EDIFACT content: {e}")
            self.state = 'error'
            self.error_message = str(e)
            return

        for segment in interchange.segments:
            _logger.info(f"Segment: {segment.tag} - {segment.elements}")
            for elem in segment.elements:
                if not isinstance(elem, (str, list)):
                    _logger.warning(f"Segment element not string or list: {repr(elem)}")

        self.message_content = interchange.serialize()

    def _edifact_invoice_get_interchange(self):
        """
        Generates and returns an EDIFACT interchange object for an invoice message.

        This method retrieves the GLN (Global Location Number) identifiers for both the sender and receiver,
        constructs the required EDIFACT sender and recipient information, sets the syntax identifier,
        and creates an interchange record using the 'base.edifact' model.

        Returns:
            recordset: The created EDIFACT interchange record.
        """

        sender_edifact = [self.sender_id.name, "14"]
        recipient_edifact = [self.receiver_id.name, "14"]
        syntax_identifier = ["UNOC", "3"]

        return self.env["base.edifact"].create_interchange(
            sender_edifact, recipient_edifact, self.id, syntax_identifier
        )

    def action_send_edifact_message(self):
        """
        Action to send the EDIFACT message.
        """
        self.ensure_one()

        lang = self.env.context.get('lang')
        mail_template = self.env.ref('weenect_edifact.email_template_edi_invoic_sagaflor', raise_if_not_found=False)
        if mail_template and mail_template.lang:
            lang = mail_template._render_lang(self.ids)[self.id]

        mail_template.email_from = self.env.user.email

        attachments = []
        attachment = self.env['ir.attachment'].create({
            'name': f"Message_{self.id}.txt",
            'type': 'binary',
            'datas': base64.b64encode(self.message_content.encode('utf-8')),
            'res_model': 'edifact.message',
            'res_id': self.id,
            'mimetype': 'application/edi'
        })
        attachments.append(attachment.id)
            
        if attachments:
            mail_template.attachment_ids = [(6, 0, attachments)]

        ctx = {
            'default_model': 'edifact.message',
            'default_res_id': self.id,
            'default_use_template': bool(mail_template),
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'force_email': True,
            'lang': lang,
        }

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
