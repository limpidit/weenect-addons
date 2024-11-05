
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    salesupply_api_host = fields.Char(string="Salesupply API url")
    salesupply_api_username = fields.Char(string="Salesupply API username")
    salesupply_api_password = fields.Char(string="Salesupply API password")
    