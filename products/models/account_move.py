from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    tracking_numbers = fields.Char(string='Numéros de Tracking', compute='_compute_tracking_numbers')
    delivery_order_numbers = fields.Char(string='Numéros de BL', compute='_compute_delivery_order_numbers')


    order_date = fields.Date(compute='_compute_order_date', string='Date de la Commande')

    def _compute_order_date(self):
        for record in self:
            record.order_date = record.invoice_origin and self.env['sale.order'].search([('name', '=', record.invoice_origin)], limit=1).date_order

    @api.depends('invoice_line_ids')
    def _compute_tracking_numbers(self):
        for record in self:
            tracking_numbers_set = set()
            
            for invoice_line in record.invoice_line_ids:
                # Accéder aux lignes de commande de vente associées à chaque ligne de facture
                sale_order_lines = invoice_line.sale_line_ids
                for sale_order_line in sale_order_lines:
                    # Accéder aux bons de livraison liés à chaque ligne de commande de vente
                    pickings = sale_order_line.order_id.picking_ids
                    for picking in pickings:
                        if picking.tracking_number:
                            tracking_numbers_set.add(picking.tracking_number)

            record.tracking_numbers = ', '.join(tracking_numbers_set)

    @api.depends('invoice_line_ids')
    def _compute_delivery_order_numbers(self):
        for record in self:
            delivery_order_numbers_set = set()
            
            for invoice_line in record.invoice_line_ids:
                # Accéder aux lignes de commande de vente associées à chaque ligne de facture
                sale_order_lines = invoice_line.sale_line_ids
                for sale_order_line in sale_order_lines:
                    # Accéder aux bons de livraison liés à chaque ligne de commande de vente
                    pickings = sale_order_line.order_id.picking_ids
                    for picking in pickings:
                        # Assumant que le numéro de bon de livraison est stocké dans un champ du modèle stock.picking
                        # Vous devrez remplacer `picking.delivery_order_number` par le nom réel du champ si différent
                        if picking.name: # Utiliser 'name' pour l'identifiant du bon de livraison
                            delivery_order_numbers_set.add(picking.name)

            # Joindre les numéros de bon de livraison en une seule chaîne séparée par des virgules
            record.delivery_order_numbers = ', '.join(delivery_order_numbers_set)

