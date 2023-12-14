from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    tracking_numbers = fields.Char(string='Numéros de Tracking', compute='_compute_tracking_numbers')

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

