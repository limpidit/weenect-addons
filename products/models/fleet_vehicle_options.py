from odoo import fields, models

class FleetVehicleOptions(models.Model):
    _name = 'fleet.vehicle.options'
    _description ='Options du véhicule'

    nom_option = fields.Char(string='Nom de l\'option', required=True)
