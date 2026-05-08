from odoo import models, fields


class VisiteEmplacement(models.Model):
    _name = "weenect.visite.emplacement"
    _description = "Emplacement de visite"
    _order = "name"

    name = fields.Char(string="Emplacement", required=True, translate=False)
    color = fields.Integer(string="Couleur", default=0)
