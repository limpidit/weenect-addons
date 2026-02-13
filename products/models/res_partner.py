from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    num_retailer=fields.Char("Numéro Retailer")
    code_bic=fields.Char(string="Code BIC")
    code_ape=fields.Char("Code APE")
    date_ouverture=fields.Date("Date d'ouverture")
    joom1_effectue=fields.Boolean("JOOM1 effectué")
    derniere_activite_tl=fields.Date("Dernière activité TL")
    province=fields.Char("Province")
    tva_tl=fields.Char("TVA TL")
    groupe_retailer=fields.Char("Groupe Retailer")

    imei_traceur=fields.Char("IMEI traceur")
    traceur_demo=fields.Boolean("Traceur de démo")

    cartes_antivol=fields.Boolean("Cartes antivol")
    pack_communication=fields.Boolean("Pack communication")
    posters=fields.Boolean("Posters")
    presentoir_orange=fields.Boolean("Présentoir Orange")

    lien_tl=fields.Char("Lien fiche TL")

    traceurs_sav_ids = fields.One2many(
        'traceurs.sav', 
        'client_id', 
        string='Traceurs')

    department = fields.Char(string="Département", compute='_compute_department', store="True")

    @api.depends('zip')
    def _compute_department(self):
        for record in self:
            record.department = record.zip[:2] if record.zip else ''

    @api.model
    def _field_to_sql(self, alias, fname, query):
        # Si l'ORM essaie de transformer ce champ en SQL (ce qu'il ne peut pas faire)
        # on intercepte l'erreur ici pour éviter le crash.
        if fname == 'property_product_pricelist':
            # On retourne une expression vide ou None selon le besoin de l'ORM
            # pour stopper la recherche SQL sur ce champ virtuel.
            return None
        return super()._field_to_sql(alias, fname, query)
