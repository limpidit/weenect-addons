
from odoo import models, fields, api, _


class StockLot(models.Model):
    _inherit = 'stock.lot'

    available_on_crosslog = fields.Boolean(string="Available on Crosslog")
    crosslog_qty = fields.Float(
        string="Crosslog quantity",
        compute='_compute_crosslog_qty',
        store=False
    )

    @api.model
    def default_get(self, fields_list):
        res = super(StockLot, self).default_get(fields_list)
        if self.env.context.get('crosslog'):
            res['available_on_crosslog'] = True
        return res

    def _compute_crosslog_qty(self):
        warehouses = self.env['crosslog.connection'].search([]).mapped('warehouse_id')
        roots = warehouses.mapped('view_location_id')

        domain_base = []
        if roots:
            domain_base = [('location_id', 'child_of', roots.ids)]

        for lot in self:
            domain = domain_base + [('lot_id', '=', lot.id)]
            quants = self.env['stock.quant'].search(domain)
           
            qty = sum(quants.mapped('quantity'))

            lot.crosslog_qty = qty


    @api.model
    def action_open_crosslog_lots(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Products lots available on Crosslog"),
            'res_model': 'stock.lot',
            'view_mode': 'list',
            'domain': [('available_on_crosslog', '=', True)],
            'context': {
                'crosslog': True,
                'group_by': ['product_id'],
            },
        }