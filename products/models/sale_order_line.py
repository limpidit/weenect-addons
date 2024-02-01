from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    order_date = fields.Datetime(related='order_id.date_order', string='Date de la commande', store=True, readonly=True)


