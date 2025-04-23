from odoo import models, fields, api
from datetime import datetime, timedelta
from math import radians, cos, sin, sqrt, atan2

class GenerateVisitesWizard(models.TransientModel):
    _name = 'visite.generate.wizard'
    _description = "Génération automatique de visites"

    # Point de départ
    client_depart_id = fields.Many2one(
        'res.partner',
        string="📌 Client de départ",
        domain="[('partner_latitude', '!=', False), ('partner_longitude', '!=', False)]"
    )
    inclure_client_depart = fields.Boolean(string="✅ Inclure dans la tournée")

    # Zone géographique
    latitude_centre = fields.Float(string="Latitude Centre", required=True, default=48.8566)
    longitude_centre = fields.Float(string="Longitude Centre", required=True, default=2.3522)
    rayon_km = fields.Float(string="Rayon en km", required=True, default=10.0)

    # Filtres client
    jours_depuis_derniere_visite = fields.Integer(string="Délai min. depuis dernière visite (jours)", required=True, default=30)
    domain_filter_id = fields.Many2one('ir.filters', string="Filtre Client", domain="[('model_id', '=', 'res.partner')]")
    tag_ids = fields.Many2many('res.partner.category', string="Étiquettes Client")

    # Génération visites
    nombre_jours_tournee = fields.Integer(string="Nombre de jours dans la tournée", required=True, default=1)
    nombre_visites_par_jour = fields.Integer(string="Nombre de visites par jour", required=True, default=5)
    date_debut_tournee = fields.Date(string="Date de début de la tournée", required=True, default=fields.Date.context_today)

    user_id = fields.Many2one('res.users', string="👔 Vendeur Assigné", required=True, default=lambda self: self.env.user)

    clients_potentiels_count = fields.Integer(
        string="Clients potentiels",
        compute="_compute_clients_potentiels_count"
    )

    filter_company=fields.Boolean("Filtrer les sociétés uniquement", default=True)

    @api.onchange('client_depart_id')
    def _onchange_client_depart_id(self):
        for wizard in self:
            if wizard.client_depart_id:
                wizard.latitude_centre = wizard.client_depart_id.partner_latitude
                wizard.longitude_centre = wizard.client_depart_id.partner_longitude

    def _distance(self, lat1, lon1, lat2, lon2):
        R = 6371  # km
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def generate_visites(self):
        visite_model = self.env['visite.visite']
        tournee_model = self.env['visite.tournee']
        client_model = self.env['res.partner']
        date_limite = datetime.now() - timedelta(days=self.jours_depuis_derniere_visite)

        domain = [('partner_latitude', '!=', False), ('partner_longitude', '!=', False)]
        if self.filter_company:
            domain.append(('is_company', '=', True))
        if self.domain_filter_id and self.domain_filter_id.domain:
            domain.extend(eval(self.domain_filter_id.domain))

        clients = client_model.search(domain)

        clients_proches = []
        for client in clients:
            if self.tag_ids and not all(tag in client.category_id for tag in self.tag_ids):
                continue

            distance = self._distance(
                self.latitude_centre, self.longitude_centre,
                client.partner_latitude, client.partner_longitude
            )

            if distance <= self.rayon_km:
                clients_proches.append((client, distance))

        clients_proches.sort(key=lambda x: x[1])
        clients_proches = [client[0] for client in clients_proches]

        if self.inclure_client_depart and self.client_depart_id and self.client_depart_id not in clients_proches:
            clients_proches.insert(0, self.client_depart_id)

        # Création de la tournée
        date_debut = self.date_debut_tournee
        date_fin = date_debut + timedelta(days=self.nombre_jours_tournee - 1)

        tournee = tournee_model.create({
            'name': f"Tournée {self.user_id.name} {date_debut.strftime('%d/%m/%Y')} - {date_fin.strftime('%d/%m/%Y')}",
            'date_debut_tournee': date_debut,
            'date_fin_tournee': date_fin,
            'user_id': self.user_id.id,
            'state': 'a_planifier',
        })

        visites_creees = 0
        total_visites = self.nombre_jours_tournee * self.nombre_visites_par_jour
        current_date = datetime.combine(date_debut, datetime.min.time())

        for client in clients_proches:
            if visites_creees >= total_visites:
                break

            derniere_visite = visite_model.search([
                ('client_id', '=', client.id)
            ], order='date_visite desc', limit=1)

            if derniere_visite and derniere_visite.date_visite >= date_limite:
                continue

            jour_offset = visites_creees // self.nombre_visites_par_jour
            date_visite = current_date + timedelta(days=jour_offset)

            visite_model.create({
                'name': f"{client.name} - {date_visite.strftime('%d/%m/%Y')}",
                'client_id': client.id,
                'date_visite': date_visite,
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

    @api.depends(
        'latitude_centre', 'longitude_centre', 'rayon_km',
        'jours_depuis_derniere_visite', 'domain_filter_id', 'tag_ids','filter_company'
    )
    def _compute_clients_potentiels_count(self):
        visite_model = self.env['visite.visite']
        for wizard in self:
            domain = [('partner_latitude', '!=', False), ('partner_longitude', '!=', False)]
            if self.filter_company:
                domain.append(('is_company', '=', True))

            if wizard.domain_filter_id and wizard.domain_filter_id.domain:
                domain.extend(eval(wizard.domain_filter_id.domain))

            clients = self.env['res.partner'].search(domain)
            date_limite = datetime.now() - timedelta(days=wizard.jours_depuis_derniere_visite)
            count = 0
            for client in clients:
                if wizard.tag_ids and not all(tag in client.category_id for tag in wizard.tag_ids):
                    continue

                distance = wizard._distance(
                    wizard.latitude_centre, wizard.longitude_centre,
                    client.partner_latitude, client.partner_longitude
                )
                if distance > wizard.rayon_km:
                    continue

                derniere_visite = visite_model.search([
                    ('client_id', '=', client.id)
                ], order='date_visite desc', limit=1)

                if derniere_visite and derniere_visite.date_visite >= date_limite:
                    continue

                count += 1

            wizard.clients_potentiels_count = count
