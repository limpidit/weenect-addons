from odoo import api,models, fields
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from odoo import exceptions, _



class FleetVehicle(models.Model):
    _inherit="fleet.vehicle"
    
    type_stock=fields.Selection([ ('avendre', 'A vendre'),('demo', 'Démo'),('pret', 'Prêt'),('courtoisie', 'Courtoisie'),('societe', 'Société')],default='avendre')
    num_affaire=fields.Char()
    num_production=fields.Char()
    prix_achat=fields.Monetary('Prix achat')
    prix_vente_prev=fields.Monetary('Prix vente prévisionnel')
    localisation=fields.Selection([ ('pl86', 'PL 86'),('pl79', 'PL 79'),('pl18', 'PL 18'),('pl37', 'PL 37'),('translese', 'Translese'),('pl36', 'PL 36'),('carrossier', 'Carrossier')],default='pl86')
    carrossier=fields.Many2one("res.partner",domain=[('is_company', '=', True)])
    prospects = fields.Many2many('crm.lead', string='Prospects')
    client_final=fields.Many2one("res.partner",domain=[('is_company', '=', True)])
    reservation_ids = fields.One2many('fleet.vehicle.reservation', 'vehicule', string='Réservations')

    display_name = fields.Char(string='Nom affiché', compute='_compute_display_name', store=True)

    has_active_opportunity = fields.Boolean(string='A une opportunité active ?', compute='_compute_has_active_opportunity')


    date_immatriculation=fields.Date()
    date_commande_daf=fields.Date()
    date_commande_client=fields.Date()
    date_production = fields.Date(string='Date de production')
    semaine_production = fields.Integer(string='Numéro de semaine de production', compute='_compute_semaine_production', store=True)
    annee_production = fields.Integer(string='Année de production', compute='_compute_annee_production', store=True)

    date_livraison_pl86 = fields.Date(string='Date de livraison PL86', compute='_compute_date_livraison_pl86', store=True, readonly=False)
    date_livraison_client = fields.Date(string='Date de livraison client', compute='_compute_date_livraison_client', store=True, readonly=False)

    date_ct=fields.Date(string="Date Contrôle Technique")
    date_derniere_revision=fields.Date(string="Date dernière révision")
    
    options = fields.Many2many('fleet.vehicle.options', string='Options')

    photo1 = fields.Binary("Photo 1", attachment=True)
    photo2 = fields.Binary("Photo 2", attachment=True)
    photo3 = fields.Binary("Photo 3", attachment=True)
    photo4 = fields.Binary("Photo 4", attachment=True)
    photo5 = fields.Binary("Photo 5", attachment=True)

    contrat_entretien = fields.Selection([
        ('non', 'NON'),
        ('care_plus', 'Care Plus'),
        ('extra_care', 'Extra Care'),
        ('flex_care', 'Flex Care'),
        ('full_care', 'Full Care'),
        ('extra_life', 'Extra Life')
    ], string='Contrat d\'entretien')

    type_garantie = fields.Selection([
        ('1+1', '1+1'),
        ('24_total', '24 total'),
        ('36_total', '36 total'),
        ('1+2', '1+2'),
        ('1+3', '1+3'),
        ('prolongation_coeos', 'Prolongation de garantie Coeos')
    ], string='Type de garantie')

    modele = fields.Many2one('modele.camion', string='Modèle de camion')

    type_camion = fields.Selection([
        ('porteur', 'Porteur'),
        ('tracteur', 'Tracteur')
    ], string='Type')

    essieux = fields.Selection([
        ('fa_4x2', 'FA 4x2'),
        ('far_6x2', 'FAR 6x2'),
        ('fas_6x2', 'FAS 6x2'),
        ('fag_6x2', 'FAG 6x2'),
        ('fan_6x2', 'FAN 6x2'),
        ('fat_6x4', 'FAT 6x4'),
        ('fak_8x2', 'FAK 8x2'),
        ('faq_8x2', 'FAQ 8x2'),
        ('fac_8x2', 'FAC 8x2'),
        ('fax_8x2', 'FAX 8x2'),
        ('fad_8x4', 'FAD 8x4'),
        ('faw_8x4', 'FAW 8x4'),
        ('ft_4,2', 'FT 4,2'),
        ('ftp_6x2', 'FTP 6x2'),
        ('ftr_6x2', 'FTR 6x2'),
        ('fts_6x2', 'FTS 6x2'),
        ('ftg_6x2', 'FTG 6x2'),
        ('ftn_6x2', 'FTN 6x2'),
        ('ftt_6x4', 'FTT 6x4'),
        ('ftm8x4', 'FTM8x4')
    ], string='Essieux', required=True)

    lead_ids = fields.Many2many('crm.lead', 'crm_lead_vehicle_rel', 'vehicle_id', 'lead_id', string='Opportunités', store=True)

    cabine = fields.Char(string='Cabine')

    motorisation = fields.Integer(string='Motorisation')

    type_boite = fields.Selection([
        ('mecanique', 'Mécanique'),
        ('auto', 'Auto')
    ], string='Type de boîte')

    ralentisseur = fields.Selection([
        ('mx', 'MX'),
        ('intarder', 'Intarder')
    ], string='Ralentisseur')

    reservoir = fields.Integer(string='Réservoir')

    type_pneu = fields.Char(string='Type de pneu')

    couleur = fields.Char(string='Couleur')

    empatement = fields.Char(string='Empattement')
    rapport_de_pont = fields.Char(string='Rapport de pont')
    remarques = fields.Text(string='Remarques')

    prise_de_force = fields.Boolean(string="Prise de force")

    carrosserie = fields.Selection([
        ('benne', 'Benne'),
        ('bi_benne', 'Bi-Benne'),
        ('amplirol', 'Amplirol'),
        ('plateau', 'Plateau'),
        ('toupie', 'Toupie'),
        ('toupie_tapis', 'Toupie Tapis'),
        ('grue', 'Grue'),
        ('bom', 'BOM'),
        ('bras_grue', 'Bras Grue'),
        ('fourgon', 'Fourgon'),
        ('citerne', 'Citerne'),
        ('beton', 'Beton'),
        ('betaille', 'Betaille'),
        ('plsc', 'PLSC'),
        ('bache', 'Bache'),
        ('autre', 'Autre')
    ], string="Carrosserie")

    autre_modele = fields.Char(string='Autre modèle')

    fichiers = fields.Many2many('ir.attachment', string="Fichiers", relation='camion_fichiers_rel', column1='camion_id', column2='fichier_id')
    sda = fields.Many2many('ir.attachment', string="SDA",relation='camion_sda_rel', column1='camion_id', column2='sda_id')
    releve_tachy = fields.Many2many(
        'fleet.vehicle.tachy',
        'fleet_vehicle_tachy_rel',  # nom de la table de liaison
        'vehicle_id',  # nom de la colonne de cette table référençant fleet.vehicle
        'tachy_id',  # nom de la colonne de cette table référençant fleet.vehicle.tachy
        string='Tachy Records',
    )

    contremarque_initiale = fields.Many2one("res.partner",domain=[('is_company', '=', True)])

    rentabilites_liees = fields.One2many(
        'rentabilite.rentabilite', # modèle cible
        'vehicle_id_renta', # champ de relation dans le modèle cible
        string='Rentabilités liées'
    )

    reservation_id = fields.Many2one('fleet.vehicle.reservation', string='Réservation')

    kilometrage = fields.Integer(string='Kilométrage')

    has_hydraulique = fields.Boolean(string='A hydraulique', compute='_compute_has_hydraulique', store=True)

    reservation_ids = fields.One2many('fleet.vehicle.reservation', 'vehicule', string='Réservations du véhicule')


    @api.depends('lead_ids')
    def _compute_has_active_opportunity(self):
        for record in self:
            record.has_active_opportunity = bool(record.lead_ids)

    @api.depends('date_production')
    def _compute_semaine_production(self):
        for record in self:
            if record.date_production:
                record.semaine_production = record.date_production.isocalendar()[1]

    @api.depends('date_production')
    def _compute_annee_production(self):
        for record in self:
            if record.date_production:
                record.annee_production = record.date_production.year

    @api.depends('date_production')
    def _compute_date_livraison_pl86(self):
        for record in self:
            if record.date_production:
                record.date_livraison_pl86 = record.date_production + timedelta(weeks=1)

    @api.depends('date_livraison_pl86')
    def _compute_date_livraison_client(self):
        for record in self:
            if record.date_livraison_pl86:
                record.date_livraison_client = record.date_livraison_pl86 + timedelta(weeks=2)

    @api.depends('options')
    def _compute_has_hydraulique(self):
        for record in self:
            record.has_hydraulique = any(option.nom_option == 'hydraulique' for option in record.options)

    @api.depends('model_id', 'essieux', 'motorisation')
    def _compute_display_name(self):
        for record in self:
            model_name = record.model_id.name if record.model_id else ""
            
            # Récupérer la deuxième partie du tuple pour le champ essieux
            essieux_dict = dict(self._fields['essieux'].selection)  # transforme la sélection en dictionnaire
            essieux_value = essieux_dict.get(record.essieux, "")  # récupère la valeur lisible
            
            motorisation_value = record.motorisation if record.motorisation else ""
            record.display_name = f"{model_name} {essieux_value} {motorisation_value}".strip()
    
    def write(self, vals):
        if 'state_id' in vals and not self.env.user.has_group('fleet.fleet_group_user'):
            raise exceptions.UserError(_('Vous n\'avez pas la permission de modifier l\'état du véhicule.'))
        return super(FleetVehicle, self).write(vals)
