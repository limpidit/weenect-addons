import requests
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    crosslog_username = fields.Char('Crosslog Username')
    crosslog_password = fields.Char('Crosslog Password')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            crosslog_username=self.env['ir.config_parameter'].sudo().get_param('crosslog.stock.username'),
            crosslog_password=self.env['ir.config_parameter'].sudo().get_param('crosslog.stock.password'),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('crosslog.stock.username', self.crosslog_username)
        self.env['ir.config_parameter'].sudo().set_param('crosslog.stock.password', self.crosslog_password)
