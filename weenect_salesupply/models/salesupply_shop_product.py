
from odoo import models, fields


class SalesupplyShopProduct(models.Model):
    _name = 'salesupply.shop.product'
    _description = "Linking products to salesupply shops"

    product_tmpl_id = fields.Many2one(comodel_name='product.template', string="Product")
    id_salesupply = fields.Integer(string="Salesupply id")
    id_shop_group = fields.Integer(string="Salesupply shop group id")
    