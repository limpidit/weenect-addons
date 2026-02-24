
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    groupe_retailer = fields.Char(string="Groupe Retailer", related='partner_id.groupe_retailer')