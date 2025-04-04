
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Crosslog
    available_on_crosslog = fields.Boolean(string="Available on Crosslog", readonly=True)

    