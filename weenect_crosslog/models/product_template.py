
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Crosslog
    available_on_crosslog = fields.Boolean(string="Available on Crosslog", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ProductTemplate, self).default_get(fields_list)
        if self.env.context.get('crosslog'):
            res['available_on_crosslog'] = True
        return res

    @api.model
    def action_open_crosslog_products(self):
        warehouses = self.env['crosslog.connection'].search([]).mapped('warehouse_id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products available on Crosslog',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('available_on_crosslog', '=', True)],
            'context': {
                'crosslog': True,
                'warehouse': warehouses.ids,
                'search_default_consumable': 1,
                'default_detailed_type': 'product',
            },
        }
    