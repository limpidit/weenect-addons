
import json

from odoo import models


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        edifact_message_object = self.env['edifact.message']
        for record in self:
            if record.model == 'edifact.message':
                ids = json.loads(record.res_ids) if record.res_ids else []
                current_message = edifact_message_object.browse(ids)
                current_message.move_ids.write({'has_been_sent': True})
        return super(MailComposer, self)._action_send_mail(auto_commit=auto_commit)
