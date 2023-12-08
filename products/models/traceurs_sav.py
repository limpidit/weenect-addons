from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TraceursSAV(models.Model):
    _name = 'traceurs.sav'
    _description = 'Traceurs SAV'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    client_id = fields.Many2one('res.partner', string='Nom client')
    product_id = fields.Many2one('product.product', string='Produit')
    imei = fields.Char(string='IMEI')
    traceur_sav_a_envoyer=fields.Boolean("A envoyer")
    traceur_sav_recu=fields.Boolean("Reçu")
    type = fields.Selection([
        ('demo', 'Démo'),
        ('sav', 'SAV')
    ], string='Type')

