from odoo import api, models, fields, tools, _

class MailThread(models.AbstractModel):
    _inherit = "mail.thread"
    
    @api.model
    def message_post(self, **kwargs):
        # Appeler la méthode parente
        message = super(MailThread, self).message_post(**kwargs)
        
        # Vérifier si le message est une note liée à un contact
        if self._name == 'res.partner' and message.subtype_id.internal == False:
            self.write({'last_note_date': fields.Date.context_today(self)})
        
        return message
