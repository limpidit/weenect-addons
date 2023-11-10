from odoo import api,models, fields
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class FleetVehicleProvision(models.Model):
    _name="fleet.vehicle.provision"
    
    vehicule_provision = fields.Many2one('fleet.vehicle', string='Véhicule')
    date_provision = fields.Date(string='Date de provision', default=fields.Date.context_today)

    montant_provision = fields.Float(string='Montant de provision', compute='_compute_montant_provision', store=True)
    montant_vr = fields.Float(string='Montant VR')
    montant_marche = fields.Float(string='Montant de marché')

    @api.depends('montant_vr', 'montant_marche')
    def _compute_montant_provision(self):
        for record in self:
            record.montant_provision = record.montant_vr - record.montant_marche
    