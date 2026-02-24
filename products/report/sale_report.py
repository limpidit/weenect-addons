
from odoo import models, fields


class SaleReport(models.Model):
    _inherit = 'sale.report'

    groupe_retailer = fields.Char(string="Groupe Retailer", readonly=True)

    def _select_sale(self):
        select_ = super()._select_sale()
        select_ += """
            ,partner.groupe_retailer AS groupe_retailer
        """
        return select_