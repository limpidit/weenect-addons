from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Tournee(models.Model):
    _name = 'visite.tournee'
    _description = "Tournée de Visites"
    _inherit = ['mail.thread', 'mail.activity.mixin']  # ✅ Ajout du chatter

    name = fields.Char(string="Nom de la tournée", required=True, tracking=True)
    date_debut_tournee = fields.Date(string="Date début de la tournée", required=True, default=fields.Date.today, tracking=True)
    date_fin_tournee = fields.Date(string="Date fin de la tournée", required=True, tracking=True)

    user_id = fields.Many2one('res.users', string="Responsable", required=True, default=lambda self: self.env.user, tracking=True)
    visite_ids = fields.One2many('visite.visite', 'tournee_id', string="Visites")

    state = fields.Selection([
        ('a_planifier', 'À planifier'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée')
    ], string="Statut", default="a_planifier", tracking=True)  # ✅ Ajout du tracking sur le statut

    @api.constrains('date_debut_tournee', 'date_fin_tournee')
    def _check_dates(self):
        for record in self:
            if record.date_fin_tournee < record.date_debut_tournee:
                raise ValidationError("La date de fin doit être postérieure ou égale à la date de début.")

    def action_afficher_plan_tournee(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f"Plan de tournée : {self.name}",
            'res_model': 'visite.visite',
            'view_mode': 'map,list,form',
            'domain': [('tournee_id', '=', self.id)],
            'context': {
                'default_tournee_id': self.id,
            },
            'target': 'current',
        }

