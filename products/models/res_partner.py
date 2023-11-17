from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    code_bic=fields.Char(string="Code BIC")
