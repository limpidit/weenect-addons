
from odoo import models


class ResPartnerIdCategory(models.Model):
    _inherit = 'res.partner.id_category'

    def validate_id_number(self, id_number):
        return
