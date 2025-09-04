
from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    crosslog_code = fields.Char(string="Crosslog code")
    crosslog_order_id = fields.Char(string="Crosslog order id")
    crosslog_synchronized = fields.Boolean(string="Synchronized with Crosslog", default=False, copy=False)
    is_transfered_to_crosslog = fields.Boolean(store=True)
    is_delivered_from_crosslog = fields.Boolean(store=True)
    is_returned_to_crosslog = fields.Boolean(store=True)

    