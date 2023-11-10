from odoo import fields, models

class FleetVehicleTachy(models.Model):
    _name = 'fleet.vehicle.tachy'
    _description ='Relevés du tachy'

    date_controle_tachy = fields.Date()
    camion=fields.Many2one("fleet.vehicle")

