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
    gocardless = fields.Boolean("GoCardless")

    @api.depends('zip')
    def _compute_department(self):
        for record in self:
            record.department = record.zip[:2] if record.zip else ''
