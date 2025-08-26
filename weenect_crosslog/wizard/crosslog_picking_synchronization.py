
from odoo import models, fields

class CrosslogPickingSynchronization(models.TransientModel):
    _name = 'crosslog.picking.synchronization'
    _description = 'Crosslog Picking Synchronization'

    api_connection_id = fields.Many2one(
        comodel_name='crosslog.connection',
        string='API Connection',
        required=True,
        help='Select the API connection to use for synchronization.',
    )

    sync_deliveries = fields.Boolean(string="Synchronize deliveries")
    sync_receptions = fields.Boolean(string="Synchronize receptions")

    def synchronize_picking(self):
        """Synchronize pickings with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        
        warehouse = self.api_connection_id.warehouse_id

        if self.synchronize_receptions:
            receptions_data = self.api_connection_id.process_get_receptions_request()
            for reception in receptions_data:
                if not picking_object.search([('crosslog_code', '=', reception['reception_code'])], limit=1):
                    picking_object.create({
                        'picking_type_id': warehouse.in_type_id.id,
                        'location_dest_id': warehouse.lot_stock_id.id,
                        'location_id': warehouse.suppliers_location_id.id,
                        'origin': reception['reception_code'],
                        'crosslog_code': reception['reception_code'],
                        'crosslog_order_id': reception['order_code'],
                        'is_delivered_from_crosslog': True,
                    })

        if self.synchronize_deliveries:
            deliveries_data = self.api_connection_id.process_get_deliveries_request()
            for delivery in deliveries_data:
                if not picking_object.search([('crosslog_code', '=', delivery['delivery_code'])], limit=1):
                    picking_object.create({
                        'picking_type_id': warehouse.out_type_id.id,
                        'location_dest_id': warehouse.customers_location_id.id,
                        'location_id': warehouse.lot_stock_id.id,
                        'origin': delivery['delivery_code'],
                        'crosslog_code': delivery['delivery_code'],
                        'crosslog_order_id': delivery['order_code'],
                        'is_transfered_to_crosslog': True,
                    })
        
        return