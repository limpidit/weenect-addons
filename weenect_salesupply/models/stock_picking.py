
from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    salesupply_code = fields.Char(string="Salesupply code")
    salesupply_synchronized = fields.Boolean(string="Synchronized with Salesupply", default=False, copy=False)
    salesupply_shipped = fields.Boolean(string="Shipped from Salesupply", default=False)
    is_transfered_to_salesupply = fields.Boolean(compute='_compute_salesupply_picking_type', store=True)
    is_delivered_from_salesupply = fields.Boolean(compute='_compute_salesupply_picking_type', store=True)
    
    @api.depends('location_id', 'location_dest_id', 'picking_type_id')
    def _compute_salesupply_picking_type(self):
        salesupply_warehouses = self.env['stock.warehouse'].search([('is_salesupply', '=', True)])
        for record in self:
            if record.location_dest_id.id in salesupply_warehouses.mapped(lambda w: w.lot_stock_id.id) and record.picking_type_id.code == 'internal':
                record.is_transfered_to_salesupply = True
                record.is_delivered_from_salesupply = False
            elif record.location_id.id in salesupply_warehouses.mapped(lambda w: w.lot_stock_id.id) and record.picking_type_id.code in 'outgoing':
                record.is_transfered_to_salesupply = False
                record.is_delivered_from_salesupply = True
            else:
                record.is_transfered_to_salesupply = False
                record.is_transfered_to_salesupply = False
        
    def _validate_internal_transfer_from_salesupply(self, salesupply_data):
        picking_object = self.env['stock.picking']
        log_object = self.env['salesupply.log']

        delivered_receptions = picking_object

        for picking in self:
            salesupply_rows = {row['ProductId']: row for row in salesupply_data.get("PurchaseOrderRows", [])}
            is_delivered = True
            for move in picking.move_ids:
                product_code = move.product_id.default_code
                shop_product = move.product_id.salesupply_shop_product_ids.filtered(lambda sp: sp.id_salesupply in salesupply_rows)
                if not shop_product:
                    log_object.log_error(_(f"Warning, the product {product_code} is not synchronized with Salesupply."))
                    is_delivered = False
                    continue
                else:
                    id_salesupply = shop_product.id_salesupply
                salesupply_row = salesupply_rows[id_salesupply]
                expected_qty = move.product_uom_qty
                delivered_qty = salesupply_row["ItemQuantityDelivered"]
                if expected_qty != delivered_qty:
                    log_object.log_info(_(f"The reception {picking.name} is not yet delivered to Salesupply"))
                    is_delivered = False
            if is_delivered:
                log_object.log_info(_(f"The reception {picking.name} is now delivered"))
                delivered_receptions |= picking

        delivered_receptions.button_validate()
        delivered_receptions.salesupply_synchronized = True
        
    @api.model
    def _return_pickings_from_salesupply(self, salesupply_returns):
        log_object = self.env['salesupply.log']
        for salesupply_json_return in salesupply_returns:
            return_code = salesupply_json_return['ReturnCode']
            
            if isinstance(salesupply_json_return, dict):
                delivery = self.search([('origin', '=', salesupply_json_return['OrderId'])])
                if not delivery:
                    log_object.log_warning(title=_(f"Could not synchronize return {return_code} because of missing delivery"))
                    continue
                
                return_wizard = self.env['stock.return.picking'].with_context({'active_id': delivery.id, 'active_model': 'stock.picking'}).create({})
                return_wizard._onchange_picking_id()
                
                try:
                    for return_row in salesupply_json_return['OrderReturnRows']:
                        line = return_wizard.product_return_moves.filtered(lambda m: m.product_id.default_code == return_row['ProductCode'])
                        line.quantity = return_row['ReturnedQuantity']
                    return_wizard.create_returns()
                except Exception as exception:
                    log_object.log_error(title=_(f"Error while returning {return_code}"), message=str(exception))

    @api.model
    def _create_shipments_from_salesupply(self, salesupply_shipments):
        log_object = self.env['salesupply.log']

        for salesupply_json_shipment in salesupply_shipments:
            