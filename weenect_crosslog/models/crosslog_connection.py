
from odoo import models, fields


class CrosslogConnection(models.Model):
    _name = 'crosslog.connection'
    _description = _name
    
    name = fields.Char(string="Name")

    # API Connection
    api_url = fields.Char(string="API url", required=True)
    username = fields.Char(string="API username", required=True)
    password = fields.Char(string="API password", required=True)

    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string="Warehouse")