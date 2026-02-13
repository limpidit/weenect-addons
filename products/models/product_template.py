from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    client_friendly_name=fields.Char(string="Dénomination client")
    ean_weenect=fields.Char(string="EAN Weenect")
