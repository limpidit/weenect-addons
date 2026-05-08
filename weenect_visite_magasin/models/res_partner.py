from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    visite_magasin_count = fields.Integer(
        string="Visites magasin",
        compute="_compute_visite_magasin_count",
    )

    def _compute_visite_magasin_count(self):
        counts = self.env["weenect.visite.magasin"].read_group(
            [("magasin_id", "in", self.ids)],
            ["magasin_id"],
            ["magasin_id"],
        )
        mapping = {c["magasin_id"][0]: c["magasin_id_count"] for c in counts}
        for rec in self:
            rec.visite_magasin_count = mapping.get(rec.id, 0)
