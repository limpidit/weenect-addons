from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = "product.template"
    