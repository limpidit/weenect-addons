
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    salesupply_api_host = fields.Char(related='company_id.salesupply_api_host', string="API url", readonly=False)
    salesupply_api_username = fields.Char(related='company_id.salesupply_api_username', string="API username", readonly=False)
    salesupply_api_password = fields.Char(related='company_id.salesupply_api_password', string="API password", readonly=False)
