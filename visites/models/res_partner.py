from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    visite_ids = fields.One2many('visite.visite', 'client_id', string="Visites")

    def action_generate_visites(self):
        """ Ouvre le wizard en passant les clients sélectionnés dans le contexte """
        return {
            "type": "ir.actions.act_window",
            "res_model": "visite.generate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_ids": self.ids},  # On passe les clients sélectionnés
        }

    def action_geo_localize(self):
        """ Géolocalise les partenaires sélectionnés en appelant la méthode geo_localize() """
        for partner in self:
            partner.geo_localize()