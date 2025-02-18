
from odoo import models, fields


class StockLot(models.Model):
    _inherit = 'stock.lot'

    is_default_salesupply_lot = fields.Boolean(string="Is default Salesupply lot", default=False)