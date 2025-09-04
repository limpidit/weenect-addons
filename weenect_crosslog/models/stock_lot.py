
from odoo import models, fields, api

class StockLot(models.Model):
    _inherit = 'stock.lot'

    is_default_crosslog_lot = fields.Boolean(string="Is default Crosslog lot", readonly=True, default=False)
    available_on_crosslog = fields.Boolean(string="Available on Crosslog", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(StockLot, self).default_get(fields_list)
        if self.env.context.get('crosslog'):
            res['available_on_crosslog'] = True
        return res

    @api.model
    def action_open_crosslog_lots(self):
        warehouses = self.env['crosslog.connection'].search([]).mapped('warehouse_id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products lots available on Crosslog',
            'res_model': 'stock.lot',
            'view_mode': 'tree,form',
            'domain': [('available_on_crosslog', '=', True)],
            'context': {
                'crosslog': True,
                'warehouse': warehouses.ids,
                'group_by': ['product_id'],
            },
        }