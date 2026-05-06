
from odoo import models, fields, api


class EdifactConfig(models.Model):
    _name = 'weenect.edifact.config'
    _description = 'Configuration EDIFACT'

    name = fields.Char(default='Configuration EDIFACT', readonly=True)

    futterhaus_sftp_host = fields.Char(string="SFTP Host", default="sftp.bela.de")
    futterhaus_sftp_port = fields.Integer(string="SFTP Port", default=22)
    futterhaus_sftp_user = fields.Char(string="SFTP Utilisateur", default="weenect")
    futterhaus_sftp_password = fields.Char(string="SFTP Mot de passe")

    @api.model
    def get_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Configuration EDIFACT'})
        return config

    def action_open_config(self):
        config = self.get_config()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configuration EDIFACT',
            'res_model': 'weenect.edifact.config',
            'res_id': config.id,
            'view_mode': 'form',
            'target': 'current',
        }
