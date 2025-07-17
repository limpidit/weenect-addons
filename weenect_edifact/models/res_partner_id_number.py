
from odoo import models, _


class ResPartnerIdNumber(models.Model):
    _inherit = 'res.partner.id_number'

    def name_get(self):
        result = []
        for record in self:
            display_name = record.partner_id.name or record.name
            result.append((record.id, display_name))
        return result