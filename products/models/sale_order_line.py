from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    order_date = fields.Datetime(related='order_id.date_order', string='Date de la commande', store=True, readonly=True)

    # Récupération du pays du client de la commande
    customer_country_id = fields.Many2one(related='order_id.partner_id.country_id', string='Pays du client', store=True, readonly=True)

    customer_language = fields.Char(compute='_compute_customer_language', string='Langue du client', store=True, readonly=True)

    @api.depends('order_id.partner_id.lang')
    def _compute_customer_language(self):
        for record in self:
            # Copier la valeur du champ lang du partenaire
            record.customer_language = record.order_id.partner_id.lang


