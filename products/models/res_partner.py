from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    num_retailer=fields.Char("Numéro Retailer")
    code_bic=fields.Char(string="Code BIC")
    code_ape=fields.Char("Code APE")
    date_ouverture=fields.Date("Date d'ouverture")
    joom1_effectue=fields.Boolean("JOOM1 effectué")
    derniere_activite_tl=fields.Date("Dernière activité TL")


