from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    imei_filled = fields.Boolean(compute='_compute_imei_filled', store=True)

