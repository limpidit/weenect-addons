from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    salesupply_api_user = fields.Char(string="Salesupply API User")
    salesupply_api_password = fields.Char(string="Salesupply API Password")
    salesupply_base_url = fields.Char(string="Salesupply Base URL")
    salesupply_location_id = fields.Many2one('stock.location', string="Salesupply Location", domain=[('usage', '!=', 'view')])

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            salesupply_api_user=self.env['ir.config_parameter'].sudo().get_param('salesupply.api_user'),
            salesupply_api_password=self.env['ir.config_parameter'].sudo().get_param('salesupply.api_password'),
            salesupply_base_url=self.env['ir.config_parameter'].sudo().get_param('salesupply.base_url'),
            salesupply_location_id=int(self.env['ir.config_parameter'].sudo().get_param('salesupply.location_id'))
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('salesupply.api_user', self.salesupply_api_user)
        self.env['ir.config_parameter'].sudo().set_param('salesupply.api_password', self.salesupply_api_password)
        self.env['ir.config_parameter'].sudo().set_param('salesupply.base_url', self.salesupply_base_url)
        self.env['ir.config_parameter'].sudo().set_param('salesupply.location_id', self.salesupply_location_id.id)
