from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class EdiParam(models.Model):
    _name = 'edi.param'
    _description = 'EDI Param'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    key = fields.Char("Clé", required=True, unique=True)  # Exemple: "gln_client"
    value = fields.Char("Valeur", required=True)  # Exemple: le code GLN

    _sql_constraints = [
    ('key_unique', 'unique(key)', 'Chaque paramètre doit avoir une clé unique.')
]
