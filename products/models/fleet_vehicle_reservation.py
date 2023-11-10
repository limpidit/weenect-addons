from odoo import api,models, fields
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class FleetVehicleReservation(models.Model):
    _name="fleet.vehicle.reservation"
    
    vehicule = fields.Many2one('fleet.vehicle', required=True, string='Véhicule', domain="[('type_stock', '=', type_stock)]")
    date_debut = fields.Date(string='Date de début', required=True, default=fields.Date.context_today)
    date_fin = fields.Date(string='Date de fin', required=True, default=lambda self: fields.Date.context_today(self) + timedelta(days=1))
    #type_stock = fields.Selection(related='vehicule.type_stock', required=True, string='Type de stock', readonly=False,
                                  #domain="[('type_stock', 'not in', ['avendre', 'societe'])]")

    def _get_type_stock_selection(self):
        # Récupérez toutes les sélections du modèle d'origine
        all_selections = self.env['fleet.vehicle'].fields_get(['type_stock'])['type_stock']['selection']
        
        # Excluez les valeurs que vous ne voulez pas
        filtered_selections = [s for s in all_selections if s[0] not in ['avendre', 'societe']]
        
        return filtered_selections

    type_stock = fields.Selection(selection=_get_type_stock_selection, string='Type de stock')
                                  
    display_name = fields.Char(string='Nom affiché', compute='_compute_display_name', store=True)

    num_affaire_vehicle = fields.Char(related='vehicule.num_affaire', string='Numéro affaire', readonly=True, store=True)


    available_vehicles = fields.Many2many('fleet.vehicle', string='Camions disponibles', compute='_compute_available_vehicles')

    client_reservation = fields.Many2one('res.partner', required=True, string='Client')
    facturable = fields.Boolean(string='Facturable')

    @api.depends('date_debut', 'date_fin', 'type_stock')
    def _compute_available_vehicles(self):
        for record in self:
            reservations = self.env['fleet.vehicle.reservation'].search([
                ('date_debut', '<=', record.date_fin),
                ('date_fin', '>=', record.date_debut)
            ])
            reserved_vehicle_ids = reservations.mapped('vehicule.id')
            available_vehicles = self.env['fleet.vehicle'].search([
                ('id', 'not in', reserved_vehicle_ids),
                ('type_stock', '=', record.type_stock)
            ])
            record.available_vehicles = [(6, 0, available_vehicles.ids)]

    @api.depends('vehicule')
    def _compute_display_name(self):
        for record in self:
            name = record.vehicule.license_plate if record.vehicule else ""
            record.display_name = name

    @api.onchange('vehicule')
    def _onchange_vehicule(self):
        self.display_name = self.vehicule.license_plate if self.vehicule else ""
