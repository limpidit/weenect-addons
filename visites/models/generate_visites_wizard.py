from odoo import models, fields, api
from datetime import datetime, timedelta
from math import radians, cos, sin, sqrt, atan2

class GenerateVisitesWizard(models.TransientModel):
    _name = 'visite.generate.wizard'
    _description = "Génération automatique de visites"

    latitude_centre = fields.Float(string="Latitude Centre", required=True, default=48.8566)
    longitude_centre = fields.Float(string="Longitude Centre", required=True, default=2.3522)
    rayon_km = fields.Float(string="Rayon en km", required=True, default=10.0)
    nombre_visites = fields.Integer(string="Nombre max de visites", required=True, default=10)
    jours_depuis_derniere_visite = fields.Integer(string="Délai minimum depuis dernière visite (jours)", required=True, default=30)

    # Sélecteur de domaine dynamique
    domain_filter_id = fields.Many2one(
        'ir.filters', 
        string="Filtre Client", 
        domain="[('model_id', '=', 'res.partner')]"
    )

    # Sélection du vendeur
    user_id = fields.Many2one('res.users', string="Vendeur Assigné", required=True, default=lambda self: self.env.user)

    def _distance(self, lat1, lon1, lat2, lon2):
        """ Calcule la distance entre deux points GPS (formule de Haversine). """
        R = 6371  # Rayon de la Terre en km
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])  # Conversion en radians

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c  # Distance en km

    def generate_visites(self):
        """ Génère une tournée et les visites associées. """
        visite_model = self.env['visite.visite']
        tournee_model = self.env['visite.tournee']
        client_model = self.env['res.partner']
        date_limite = datetime.now() - timedelta(days=self.jours_depuis_derniere_visite)

        # Construire le domaine de recherche des clients
        domain = [('partner_latitude', '!=', False), ('partner_longitude', '!=', False)]
        if self.domain_filter_id and self.domain_filter_id.domain:
            domain.extend(eval(self.domain_filter_id.domain))

        # Création de la tournée avec le vendeur sélectionné
        tournee = tournee_model.create({
            'name': f"Tournée {datetime.today().strftime('%Y-%m-%d')}",
            'date_debut_tournee': fields.Date.today(),
            'date_fin_tournee': fields.Date.today(),
            'user_id': self.user_id.id,
            'state': 'a_planifier',
        })

        # Recherche des clients en fonction du domaine dynamique
        clients = client_model.search(domain)

        # Filtrer les clients dans le rayon donné
        clients_proches = []
        for client in clients:
            distance = self._distance(
                self.latitude_centre, self.longitude_centre,
                client.partner_latitude, client.partner_longitude
            )
            if distance <= self.rayon_km:
                clients_proches.append((client, distance))

        # Trier les clients par distance
        clients_proches.sort(key=lambda x: x[1])
        clients_proches = [client[0] for client in clients_proches]  

        visites_creees = 0
        for client in clients_proches:
            if visites_creees >= self.nombre_visites:
                break

            # Trouver la dernière visite du client
            derniere_visite = visite_model.search([
                ('client_id', '=', client.id)
            ], order='date_visite desc', limit=1)

            if not derniere_visite or derniere_visite.date_visite < date_limite:
                visite_model.create({
                    'name': f"Visite {datetime.today().strftime('%Y-%m-%d')}",
                    'client_id': client.id,
                    'date_visite': fields.Datetime.now(),
                    'user_id': self.user_id.id,
                    'tournee_id': tournee.id,
                })
                visites_creees += 1

        return {
            'effect': {
                'fadeout': 'slow',
                'message': f"{visites_creees} visites générées dans la tournée {tournee.name}.",
                'type': 'rainbow_man',
            }
        }
