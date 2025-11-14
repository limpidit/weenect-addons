
from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _set_done_from_reserved(self, receipt_qty):
        total_qty_done = 0
        for ml in self.move_line_ids:
            total_qty_done += ml.qty_done
            
        if total_qty_done != receipt_qty:
            for ml in self.move_line_ids:
                ml.qty_done = ml.reserved_uom_qty