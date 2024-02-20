from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    order_date = fields.Datetime(related='order_id.date_order', string='Date de la commande', store=True, readonly=True)

    # Récupération du pays du client de la commande
    customer_country_id = fields.Many2one(related='order_id.partner_id.country_id', string='Pays du client', store=True, readonly=True)

    customer_language = fields.Char(compute='_compute_customer_language', string='Langue du client', store=True, readonly=True)

    # Ajout du champ effective_date lié à la commande de vente
    commitment_date = fields.Datetime(related='order_id.commitment_date', string='Date de Livraison Annoncée', store=True, readonly=True)

    # Supposons que le champ department est un champ Char dans res.partner
    partner_department = fields.Char(compute='_compute_partner_department', string='Département du Client', store=True, readonly=True)

    @api.depends('order_id.partner_id.department')
    def _compute_partner_department(self):
        for record in self:
            # Copier la valeur du champ department du partenaire
            record.partner_department = record.order_id.partner_id.department

    @api.depends('order_id.partner_id.lang')
    def _compute_customer_language(self):
        for record in self:
            # Copier la valeur du champ lang du partenaire
            record.customer_language = record.order_id.partner_id.lang


