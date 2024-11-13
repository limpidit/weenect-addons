
from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_salesupply = fields.Boolean(string="Salesupply", default=False)

    id_salesupply = fields.Integer(string="Salesupply id")
    name_salesupply = fields.Char(string="Salesupply name")
    shop_id = fields.Many2one(comodel_name='salesupply.shop', string="Shop")