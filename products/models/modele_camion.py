from odoo import fields, models

class ModeleCamion(models.Model):
    _name = 'modele.camion'
    _description ='modele de camion'

    name = fields.Char(string='Modèle de camion', required=True)
