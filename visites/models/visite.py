from odoo import models, fields, api
from datetime import datetime

class Visite(models.Model):
    _name = 'visite.visite'
    _description = 'Gestion des Visites'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_name(self):
        """ Génère un nom par défaut au format 'Visite YYYY-MM-DD' """
        return f"Visite {datetime.today().strftime('%Y-%m-%d')}"

    name = fields.Char(string="Nom", required=True, default=_default_name)
    user_id = fields.Many2one('res.users', string="Utilisateur", required=True, default=lambda self: self.env.user, tracking=True)
    date_visite = fields.Datetime(string="Date visite", required=True, default=fields.Datetime.now, tracking=True)
    client_id = fields.Many2one('res.partner', string="Client", required=True, tracking=True)
    photos = fields.Many2many('ir.attachment', string="Photos")
    resume = fields.Text(string="Résumé", tracking=True)
    tag_ids = fields.Many2many('crm.tag', string="Tags")

    # Statut de la visite
    state = fields.Selection([
        ('a_planifier', 'À planifier'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée')
    ], string="Statut", default="a_planifier", tracking=True)

    # Tournée associée
    tournee_id = fields.Many2one('visite.tournee', string="Tournée")

    # Champs calculés pour récupérer les coordonnées GPS du client
    partner_latitude = fields.Float(string="Latitude", compute="_compute_partner_coords", store=True)
    partner_longitude = fields.Float(string="Longitude", compute="_compute_partner_coords", store=True)

    @api.depends('client_id')
    def _compute_partner_coords(self):
        for record in self:
            record.partner_latitude = record.client_id.partner_latitude if record.client_id else 0.0
            record.partner_longitude = record.client_id.partner_longitude if record.client_id else 0.0
