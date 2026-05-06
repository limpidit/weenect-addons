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
    nouveau_revendeur = fields.Boolean(string="Nouveau revendeur")
    emplacement = fields.Char(string="Emplacement")
    date_visite = fields.Date(
        string="Date de visite",
        default=fields.Date.today,
        required=True,
        tracking=True,
    )

    # ── Visibilité produit ────────────────────────────────────────────────────
    produit_visible = fields.Boolean(string="Produit visible")
    presentoir_en_place = fields.Boolean(string="Présentoir en place")
    plv_visible = fields.Boolean(string="PLV visible")
    plv_bon_emplacement = fields.Boolean(string="PLV au bon emplacement")
    traceur_demo_actif = fields.Boolean(string="Traceur démo actif")
    vendeur_forme = fields.Boolean(string="Vendeur formé")
    vendeur_implique = fields.Boolean(string="Vendeur impliqué")
    engagement_responsable = fields.Selection(
        [("faible", "Faible"), ("moyen", "Moyen"), ("fort", "Fort")],
        string="Engagement du responsable",
    )
    volume_ventes_mensuel = fields.Selection(
        [
            ("lt10", "Moins de 10"),
            ("10_30", "10 à 30"),
            ("30_100", "30 à 100"),
            ("gt100", "Plus de 100"),
        ],
        string="Volume de ventes mensuel",
    )

    # ── PLV ───────────────────────────────────────────────────────────────────
    plv_presentoir = fields.Boolean(string="Présentoir")
    plv_affiche_promo = fields.Boolean(string="Affiche promo")
    plv_jeu = fields.Boolean(string="Jeu")
    plv_poster = fields.Boolean(string="Poster")
    plv_flyers = fields.Boolean(string="Flyers")
    plv_sticker_sol = fields.Boolean(string="Sticker au sol")
    plv_autre = fields.Char(string="Autre PLV")

    # ── Suivi & Actions ───────────────────────────────────────────────────────
    action_calendrier_offres = fields.Boolean(string="Envoyer calendrier des offres")
    action_videos_formation = fields.Boolean(string="Envoyer vidéos de formation")
    action_formation_traceur = fields.Boolean(string="Planifier formation traceur démo")
    action_autre = fields.Char(string="Autre action")

    # ── CR et Ventes ─────────────────────────────────────────────────────────
    cr_de_visite = fields.Text(string="CR de visite", tracking=True)
    ventes_realisees = fields.Text(string="Ventes réalisées")
    expedition_a_prevoir = fields.Boolean(string="Expédition à prévoir")

    # ── Objectif & Concurrence ────────────────────────────────────────────────
    nature_visite = fields.Selection(
        [("suivi", "Suivi"), ("sav", "SAV"), ("formation", "Formation"), ("autre", "Autre")],
        string="Nature de la visite",
    )
    concurrent_tractive = fields.Boolean(string="Tractive")
    concurrent_dogtra = fields.Boolean(string="Dogtra")
    concurrent_airtag = fields.Boolean(string="AirTag")
    concurrent_autre = fields.Char(string="Autre concurrent")

    # ── Score & Priorité (calculés) ───────────────────────────────────────────
    score_qualite = fields.Integer(
        string="Score qualité",
        compute="_compute_score_priorite",
        store=True,
    )
    priorite = fields.Selection(
        [("urgent", "Urgent"), ("a_travailler", "À travailler"), ("bon_niveau", "Bon niveau")],
        string="Priorité",
        compute="_compute_score_priorite",
        store=True,
    )

    # ── Photos ────────────────────────────────────────────────────────────────
    photo_1 = fields.Binary(string="Photo 1", attachment=True)
    photo_2 = fields.Binary(string="Photo 2", attachment=True)
    photo_3 = fields.Binary(string="Photo 3", attachment=True)
    photo_4 = fields.Binary(string="Photo 4", attachment=True)
    photo_5 = fields.Binary(string="Photo 5", attachment=True)
    photo_6 = fields.Binary(string="Photo 6", attachment=True)

    # ── Compute ───────────────────────────────────────────────────────────────
    @api.depends(
        "produit_visible", "presentoir_en_place", "plv_visible", "plv_bon_emplacement",
        "traceur_demo_actif", "vendeur_forme", "vendeur_implique",
        "engagement_responsable", "volume_ventes_mensuel", "nouveau_revendeur",
    )
    def _compute_score_priorite(self):
        engagement_pts = {"faible": 0, "moyen": 10, "fort": 20}
        volume_pts = {"lt10": 0, "10_30": 7, "30_100": 15, "gt100": 20}

        for rec in self:
            visuels = sum([
                rec.produit_visible,
                rec.presentoir_en_place,
                rec.plv_visible,
                rec.plv_bon_emplacement,
                rec.traceur_demo_actif,
                rec.vendeur_forme,
                rec.vendeur_implique,
            ]) * 5
            eng = engagement_pts.get(rec.engagement_responsable, 0)
            vol = volume_pts.get(rec.volume_ventes_mensuel, 0)

            if rec.nouveau_revendeur:
                score = int(round((visuels + eng) * 100 / 55)) if (visuels + eng) else 0
            else:
                score = visuels + eng + vol

            rec.score_qualite = score

            if score < 50:
                rec.priorite = "urgent"
            elif score < 80:
                rec.priorite = "a_travailler"
            else:
                rec.priorite = "bon_niveau"

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
        plv_fields = {
            "plv_presentoir", "plv_affiche_promo", "plv_jeu",
            "plv_poster", "plv_flyers", "plv_sticker_sol", "plv_autre",
        }
        if suivi_fields & set(vals):
            self._handle_suivi_activities()
        if plv_fields & set(vals):
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
        plv_map = [
            ("plv_presentoir", "Envoyer présentoir"),
            ("plv_affiche_promo", "Envoyer affiche promo"),
            ("plv_jeu", "Envoyer jeu"),
            ("plv_poster", "Envoyer poster"),
            ("plv_flyers", "Envoyer flyers"),
            ("plv_sticker_sol", "Envoyer sticker au sol"),
        ]
        for rec in self:
            mag_name = rec.magasin_id.name if rec.magasin_id else ""
            summaries = []
            for field, label in plv_map:
                if getattr(rec, field):
                    summaries.append(f"{label} - {mag_name}")
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
