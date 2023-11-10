from odoo import api, models, fields, tools

class CrmLead(models.Model):
    _inherit = "crm.lead"

    vehicle_ids = fields.Many2many('fleet.vehicle', 'crm_lead_vehicle_rel', 'lead_id', 'vehicle_id', string="Véhicules")
    essieux_camion_opportunite = fields.Char(string='Essieux', compute='_compute_vehicle_details')
    model_camion_opportunite = fields.Char(string='Modèle', compute='_compute_vehicle_details')
    type_camion_opportunite = fields.Char(string='Type', compute='_compute_vehicle_details')
    motorisation_camion_opportunite = fields.Integer(string='Motorisation', compute='_compute_vehicle_details')

    x_code_departement = fields.Char(string='Code département')
    x_code_postal = fields.Char(string='Code postal')
    x_ville = fields.Char(string='Ville')
    x_date_immatriculation = fields.Date(string='Date d\'immatriculation')
    x_annee_carte_grise = fields.Char(string='Année de carte grise')
    x_marque = fields.Char(string='Marque')
    x_numero_serie = fields.Char(string='Numéro de série')
    x_genre = fields.Char(string='Genre')
    x_ptr = fields.Float(string='PTR')
    x_ptac = fields.Float(string='PTAC')
    x_carrosserie = fields.Char(string='Carrosserie')
    x_profil_client = fields.Char(string='Profil client')
    x_protocole_daf = fields.Char(string='Protocole DAF')
    x_regroupement_daf = fields.Char(string='Regroupement DAF')
    x_siret = fields.Char(string='SIRET')
    x_immatriculation = fields.Char(string='Immatriculation')
    x_charge_utile = fields.Float(string='Charge utile')
    x_cylindree = fields.Integer(string='Cylindrée')
    x_denomination = fields.Char(string='Dénomination')
    x_poids_a_vide = fields.Integer(string='Poids à vide')
    x_energie=fields.Char(string="Energie")
    x_daf_connect=fields.Selection([
        ('Oui', 'Oui'),
        ('Non', 'Non'),
    ], string='DAF Connect')

    specifications_vehicule = fields.Text(string='Spécifications Véhicule')


    @api.depends('vehicle_ids')
    def _compute_vehicle_details(self):
        for record in self:
            # Modification pour gérer plusieurs véhicules
            essieux_list = [dict(v._fields['essieux'].selection).get(v.essieux) for v in record.vehicle_ids if v.essieux]
            record.essieux_camion_opportunite = ', '.join(essieux_list)
            
            model_list = [v.model_id.name for v in record.vehicle_ids]
            record.model_camion_opportunite = ', '.join(model_list)
            
            motorisation_list = [v.motorisation for v in record.vehicle_ids]
            record.motorisation_camion_opportunite = ', '.join(map(str, motorisation_list))
            
            type_camion_list = [dict(v._fields['type_camion'].selection).get(v.type_camion) for v in record.vehicle_ids]
            record.type_camion_opportunite = ', '.join(type_camion_list)
                
    def convert_opportunity(self, partner_id, user_ids=False, team_id=False):
        # Appeler la méthode parent pour obtenir le résultat (qui contient le nouveau partenaire, s'il est créé)
        result = super(CrmLead, self).convert_opportunity(partner_id, user_ids, team_id)

        # Si la conversion a réussi
        if result:
            for lead in self:
                # Si un partenaire est associé au lead, mettre à jour les champs nécessaires
                if lead.partner_id:
                    lead.partner_id.write({
                        'code_departement': lead.x_code_departement,
                        'zip': lead.x_code_postal,
                        'city': lead.x_ville,  # Ajout du champ x_ville mappé au champ city
                        'profil_client': lead.x_profil_client,  # Ajout du champ x_profil_client mappé au champ profil_client
                        'protocole_daf': lead.x_protocole_daf,  # Ajout du champ x_protocole_daf mappé au champ protocole_daf
                        'regroupement_daf': lead.x_regroupement_daf  # Ajout du champ x_regroupement_daf mappé au champ regroupement_daf
                    })

        return result



