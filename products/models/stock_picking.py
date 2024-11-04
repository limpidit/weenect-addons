from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_number = fields.Char(string='Numéro de Tracking')
    imei_filled = fields.Boolean(string='IMEI Enregistrés')
    avoir_genere = fields.Boolean(string="Avoir généré", default=False)


    def write(self, values):
        res = super(StockPicking, self).write(values)
        if 'imei_filled' in values:
            self._update_sale_order_imei_filled()
        return res

    def _update_sale_order_imei_filled(self):
        for picking in self:
            sale_order = self.env['sale.order'].search([('name', '=', picking.origin)])
            if sale_order:
                imei_filled = any(picking.imei_filled for picking in sale_order.picking_ids)
                sale_order.imei_filled = imei_filled

    @api.model
    def create(self, vals):
        new_record = super(StockPicking, self).create(vals)
        new_record._update_sale_order_imei_filled()
        return new_record

