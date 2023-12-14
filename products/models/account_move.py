from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    tracking_numbers = fields.Char(string='Numéros de Tracking', compute='_compute_tracking_numbers')

    @api.depends('invoice_line_ids.sale_line_ids.order_id.picking_ids')
    def _compute_tracking_numbers(self):
        for record in self:
            pickings = record.mapped('invoice_line_ids.sale_line_ids.order_id.picking_ids')
            tracking_numbers = ', '.join(pickings.mapped('tracking_number'))
            record.tracking_numbers = tracking_numbers

