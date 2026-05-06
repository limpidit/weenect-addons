import datetime
from odoo import models, fields, api


class VisiteMagasin(models.Model):
    _name = "weenect.visite.magasin"
    _description = "Visite Magasin"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "magasin_id"

    # ── Identification ────────────────────────────────────────────────────────
    magasin_id = fields.Many2one(
        "res.partner",
        string="Magasin",
        required=True,
        domain=[("is_company", "=", True)],
        tracking=True,
    )
    date_visite = fields.Date(
        string="Date de visite",
        default=fields.Date.today,
        required=True,
        tracking=True,
    )
    commercial_id = fields.Many2one(
        "res.users",
        string="Commercial",
        default=lambda self: self.env.user,
        tracking=True,
    )
    emplacement = fields.Char(string="Emplacement")
    nouveau_revendeur = fields.Boolean(string="Nouveau revendeur")

    # ── Score & Priorité (calculés) ───────────────────────────────────────────
    score_visite = fields.Integer(
        string="Score visite",
        compute="_compute_score_priorite",
        store=True,
    )
    priorite_commerciale = fields.Selection(
        [("urgent", "Urgent"), ("a_travailler", "À travailler"), ("bon_niveau", "Bon niveau")],
        string="Priorité commerciale",
        compute="_compute_score_priorite",
        store=True,
        tracking=True,
    )

    # ── Info générale — Personnes rencontrées ─────────────────────────────────
    personne_rencontree_ids = fields.Many2many(
        "res.partner",
        "visite_magasin_partner_rel",
        "visite_id",
        "partner_id",
        string="Personnes rencontrées",
    )

    # ── Objectif de visite ────────────────────────────────────────────────────
    visite_suivi = fields.Boolean(string="Visite suivi")
    visite_sav = fields.Boolean(string="Visite SAV")
    visite_formation = fields.Boolean(string="Visite formation")
    visite_objectif_autre = fields.Char(string="Autre")

    # ── Concurrence ───────────────────────────────────────────────────────────
    concurrent_kippy = fields.Boolean(string="Kippy")
    concurrent_tractive = fields.Boolean(string="Tractive")
    concurrent_garmin = fields.Boolean(string="Garmin")
    concurrent_dogtra = fields.Boolean(string="Dogtra")
    concurrent_invoxia = fields.Boolean(string="Invoxia")
    concurrent_airtag = fields.Boolean(string="Airtag")
    concurrent_autre = fields.Char(string="Autre")

    # ── Visibilité produit ────────────────────────────────────────────────────
    produit_visible = fields.Boolean(string="Produit Visible")
    bon_emplacement = fields.Boolean(string="Bon emplacement")
    plv_visible = fields.Boolean(string="PLV visible")
    traceur_demo_actif = fields.Boolean(string="Traceur demo actif et utilisé")
    double_implantation = fields.Boolean(string="Double implantation")
    vendeur_deja_forme = fields.Boolean(string="Vendeur déjà formé")
    vendeur_forme_visite = fields.Boolean(string="Vendeur formé pendant la visite")
    vendeur_implique = fields.Boolean(string="Vendeur impliqué")

    # ── PLV — Présentoir ──────────────────────────────────────────────────────
    plv_presentoir_deja = fields.Boolean(string="Déjà installé")
    plv_presentoir_visite = fields.Boolean(string="Installé pendant la visite")
    plv_presentoir_envoyer = fields.Boolean(string="À envoyer")

    # ── PLV — Affiche promo ───────────────────────────────────────────────────
    plv_affiche_deja = fields.Boolean(string="Déjà installée")
    plv_affiche_visite = fields.Boolean(string="Installée pendant la visite")
    plv_affiche_envoyer = fields.Boolean(string="À envoyer")

    # ── PLV — Jeu ─────────────────────────────────────────────────────────────
    plv_jeu_deja = fields.Boolean(string="Déjà installé")
    plv_jeu_visite = fields.Boolean(string="Installé pendant la visite")
    plv_jeu_envoyer = fields.Boolean(string="À envoyer")

    # ── PLV — Poster magasin ──────────────────────────────────────────────────
    plv_poster_deja = fields.Boolean(string="Déjà installé")
    plv_poster_visite = fields.Boolean(string="Installé pendant la visite")
    plv_poster_envoyer = fields.Boolean(string="À envoyer")

    # ── PLV — Autres ─────────────────────────────────────────────────────────
    plv_flyers = fields.Boolean(string="Flyers mag")
    plv_sticker_sol = fields.Boolean(string="Sticker au sol")
    plv_autre = fields.Char(string="Autre")

    # ── Suivi & Actions ───────────────────────────────────────────────────────
    volume_magasin = fields.Selection(
        [("faible", "Faible"), ("moyen", "Moyen"), ("fort", "Fort")],
        string="Volume magasin",
        help="Faible : < 1 vente/mois | Moyen : 1 à 4 | Fort : + de 4 par mois",
    )
    engagement_responsable = fields.Selection(
        [("faible", "Faible"), ("moyen", "Moyen"), ("fort", "Fort")],
        string="Engagement responsable",
    )
    action_calendrier_offres = fields.Boolean(string="Envoyer calendrier des offres")
    action_videos_formation = fields.Boolean(string="Envoyer vidéos de formation")
    action_formation_traceur = fields.Boolean(string="Planifier formation traceur démo")
    action_autre = fields.Char(string="Autres")

    # ── CR de visite ──────────────────────────────────────────────────────────
    cr_de_visite = fields.Text(string="CR de visite", tracking=True)

    # ── Ventes ────────────────────────────────────────────────────────────────
    expedition_a_prevoir = fields.Boolean(string="Expédition à prévoir")
    ventes_realisees = fields.Text(string="Ventes réalisées")

    # ── Photos ────────────────────────────────────────────────────────────────
    photo_1 = fields.Binary(string="Photo 1", attachment=True)
    photo_2 = fields.Binary(string="Photo 2", attachment=True)
    photo_3 = fields.Binary(string="Photo 3", attachment=True)
    photo_4 = fields.Binary(string="Photo 4", attachment=True)
    photo_5 = fields.Binary(string="Photo 5", attachment=True)
    photo_6 = fields.Binary(string="Photo 6", attachment=True)

    # ── Compute ───────────────────────────────────────────────────────────────
    @api.depends(
        "produit_visible", "bon_emplacement", "plv_visible", "traceur_demo_actif",
        "double_implantation", "vendeur_deja_forme", "vendeur_forme_visite", "vendeur_implique",
        "engagement_responsable", "volume_magasin", "nouveau_revendeur",
    )
    def _compute_score_priorite(self):
        engagement_pts = {"faible": 0, "moyen": 10, "fort": 20}
        volume_pts = {"faible": 0, "moyen": 10, "fort": 20}

        for rec in self:
            vendeur_forme = rec.vendeur_deja_forme or rec.vendeur_forme_visite
            visuels = sum([
                rec.produit_visible,
                rec.bon_emplacement,
                rec.plv_visible,
                rec.traceur_demo_actif,
                rec.double_implantation,
                vendeur_forme,
                rec.vendeur_implique,
            ]) * 5

            eng = engagement_pts.get(rec.engagement_responsable, 0)
            vol = volume_pts.get(rec.volume_magasin, 0)

            if rec.nouveau_revendeur:
                score = int(round((visuels + eng) * 100 / 55)) if (visuels + eng) else 0
            else:
                score = visuels + eng + vol

            rec.score_visite = score

            if score < 50:
                rec.priorite_commerciale = "urgent"
            elif score < 80:
                rec.priorite_commerciale = "a_travailler"
            else:
                rec.priorite_commerciale = "bon_niveau"

    # ── Automatisations ───────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._handle_suivi_activities()
            rec._handle_plv_activities()
            rec._handle_expedition_activity()
            rec._handle_cr_chatter()
        return records

    def write(self, vals):
        res = super().write(vals)
        suivi_fields = {
            "action_calendrier_offres", "action_videos_formation",
            "action_formation_traceur", "action_autre",
        }
        plv_envoyer_fields = {
            "plv_presentoir_envoyer", "plv_affiche_envoyer",
            "plv_jeu_envoyer", "plv_poster_envoyer",
            "plv_flyers", "plv_sticker_sol", "plv_autre",
        }
        if suivi_fields & set(vals):
            self._handle_suivi_activities()
        if plv_envoyer_fields & set(vals):
            self._handle_plv_activities()
        if "expedition_a_prevoir" in vals:
            self._handle_expedition_activity()
        if "cr_de_visite" in vals:
            self._handle_cr_chatter()
        return res

    def _schedule_activity(self, res_model, res_id, summary):
        deadline = datetime.date.today() + datetime.timedelta(days=7)
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        existing = self.env["mail.activity"].search([
            ("res_model", "=", res_model),
            ("res_id", "=", res_id),
            ("summary", "=", summary),
        ], limit=1)
        if not existing:
            self.env["mail.activity"].create({
                "res_model_id": self.env["ir.model"]._get_id(res_model),
                "res_id": res_id,
                "activity_type_id": activity_type.id,
                "summary": summary,
                "date_deadline": deadline,
                "user_id": self.env.user.id,
            })

    def _handle_suivi_activities(self):
        for rec in self:
            summaries = []
            if rec.action_calendrier_offres:
                summaries.append("Envoyer calendrier des offres")
            if rec.action_videos_formation:
                summaries.append("Envoyer vidéos de formation")
            if rec.action_formation_traceur:
                summaries.append("Planifier formation traceur démo")
            if rec.action_autre and rec.action_autre.strip():
                summaries.append("Autre action : " + rec.action_autre[:100])
            for summary in summaries:
                self._schedule_activity("weenect.visite.magasin", rec.id, summary)
                if rec.magasin_id:
                    self._schedule_activity("res.partner", rec.magasin_id.id, summary)

    def _handle_plv_activities(self):
        for rec in self:
            mag_name = rec.magasin_id.name if rec.magasin_id else ""
            summaries = []
            if rec.plv_presentoir_envoyer:
                summaries.append(f"Envoyer présentoir - {mag_name}")
            if rec.plv_affiche_envoyer:
                summaries.append(f"Envoyer affiche promo - {mag_name}")
            if rec.plv_jeu_envoyer:
                summaries.append(f"Envoyer jeu - {mag_name}")
            if rec.plv_poster_envoyer:
                summaries.append(f"Envoyer poster - {mag_name}")
            if rec.plv_flyers:
                summaries.append(f"Envoyer flyers - {mag_name}")
            if rec.plv_sticker_sol:
                summaries.append(f"Envoyer sticker au sol - {mag_name}")
            if rec.plv_autre and rec.plv_autre.strip():
                summaries.append("Envoyer PLV autre : " + rec.plv_autre[:80])
            for summary in summaries:
                self._schedule_activity("weenect.visite.magasin", rec.id, summary)
                if rec.magasin_id:
                    self._schedule_activity("res.partner", rec.magasin_id.id, summary)

    def _handle_expedition_activity(self):
        for rec in self:
            if not (rec.expedition_a_prevoir and rec.magasin_id):
                continue
            summary = "Expédier commandes - " + (rec.magasin_id.name or "magasin")
            self._schedule_activity("weenect.visite.magasin", rec.id, summary)
            self._schedule_activity("res.partner", rec.magasin_id.id, summary)

    def _handle_cr_chatter(self):
        for rec in self:
            cr = rec.cr_de_visite
            if not (rec.magasin_id and cr and cr.strip()):
                continue
            subject = f"CR visite (#{rec.id})"
            existing = self.env["mail.message"].search([
                ("model", "=", "res.partner"),
                ("res_id", "=", rec.magasin_id.id),
                ("subject", "=", subject),
            ], limit=1)
            if not existing:
                rec.magasin_id.message_post(body=cr, subject=subject)
