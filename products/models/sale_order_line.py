from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    language_id = fields.Many2one('res.lang', 'Language', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['country_id'] = ", s.partner_id.country_id as country_id"
        fields['language_id'] = ", s.partner_id.lang as language_id"
        groupby += ', s.partner_id.country_id, s.partner_id.lang'
        return super(SaleOrderLine, self)._query(with_clause, fields, groupby, from_clause)
