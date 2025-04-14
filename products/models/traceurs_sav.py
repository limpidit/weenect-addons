from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class TraceursSAV(models.Model):
    _name = 'traceurs.sav'
    _description = 'Traceurs SAV'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    client_id = fields.Many2one('res.partner', string='Nom client')
    product_id = fields.Many2one('product.product', string='Produit')
    imei = fields.Char(string='IMEI')
    traceur_sav_a_envoyer=fields.Boolean("A envoyer par Weenect (après réception)")
    traceur_sav_recu=fields.Boolean("Reçu par Weenect (envoyé par le client)")
    traceur_sav_termine=fields.Boolean("Terminé")
    type = fields.Selection([
        ('demo', 'Démo'),
        ('sav', 'SAV')
    ], string='Type')
    traceur_demo_realisee=fields.Boolean("Démo réalisée")
    date_demo = fields.Date(string="Date de la démonstration")



    @api.onchange('traceur_sav_termine')
    def _onchange_traceur_sav_termine(self):
        if self.traceur_sav_termine and self.traceur_sav_a_envoyer:
            self.traceur_sav_a_envoyer = False

    @api.constrains('traceur_demo_realisee', 'imei')
    def _check_traceur_demo_realisee(self):
        for record in self:
            if record.traceur_demo_realisee and not record.imei:
                raise ValidationError(_("Vous ne pouvez pas cocher 'Démo réalisée' si l'IMEI n'est pas renseigné."))

    @api.onchange('traceur_demo_realisee')
    def _onchange_traceur_demo_realisee(self):
        if self.traceur_demo_realisee:
            if not self.imei:
                self.traceur_demo_realisee = False
                return {
                    'warning': {
                        'title': _("Attention"),
                        'message': _("Vous devez renseigner l'IMEI avant de marquer la démo comme réalisée."),
                    }
                }
            # Remplissage automatique de la date si non renseignée
            if not self.date_demo:
                self.date_demo = date.today()
