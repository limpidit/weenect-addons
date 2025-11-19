
from odoo import models, api


class ResPartnerIdNumber(models.Model):
    _inherit = 'res.partner.id_number'

    @api.depends('partner_id')
    def _compute_display_name(self):
        super()._compute_display_name()
        for id_number in self:
            id_number.display_name = id_number.partner_id.name or id_number.name