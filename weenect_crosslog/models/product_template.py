
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_on_crosslog = fields.Boolean(string="Available on Crosslog", readonly=True)
    crosslog_qty = fields.Float(string="Crosslog quantity",compute='_compute_crosslog_qty',store=False)

    @api.model
    def default_get(self, fields_list):
        res = super(ProductTemplate, self).default_get(fields_list)
        if self.env.context.get('crosslog'):
            res['available_on_crosslog'] = True
        return res

    def _compute_crosslog_qty(self):
        Quant = self.env['stock.quant']

        warehouses = self.env['crosslog.connection'].search([]).mapped('warehouse_id')
        roots = warehouses.mapped('view_location_id')

        domain_base = []
        if roots:
            domain_base = [('location_id', 'child_of', roots.ids)]

        for product in self:
            if not roots:
                product.crosslog_qty = 0.0
                continue

            domain = domain_base + [
                ('product_id', '=', product.id),
            ]

            quants = Quant.search(domain)
            qty = sum(quants.mapped('quantity'))

            product.crosslog_qty = qty

    @api.model
    def action_open_crosslog_products(self):
        warehouses = self.env['crosslog.connection'].search([]).mapped('warehouse_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _("Products available on Crosslog"),
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('weenect_crosslog.crosslog_product_template_list').id, 'list'),
                (False, 'form'),
            ],
            'domain': [('available_on_crosslog', '=', True)],
            'context': {
                'crosslog': True,
                'warehouse': warehouses.ids,
                'search_default_consumable': 1,
                'default_detailed_type': 'product',
            },
        }
    