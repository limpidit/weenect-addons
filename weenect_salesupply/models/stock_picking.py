
from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    salesupply_synchronized = fields.Boolean(string="Synchronized with Salesupply", default=False)
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
        logs = log_object

        delivered_receptions = picking_object

        for picking in self:
            salesupply_rows = {row['ProductId']: row for row in salesupply_data.get("PurchaseOrderRows", [])}
            is_delivered = True
            for move in picking.move_ids:
                product_code = move.product_id.default_code
                shop_product = move.product_id.salesupply_shop_product_ids.filtered(lambda sp: sp.id_salesupply in salesupply_rows)
                if not shop_product:
                    logs |= log_object.log_error(_(f"Warning, the product {product_code} is not synchronized with Salesupply."))
                    is_delivered = False
                    continue
                else:
                    id_salesupply = shop_product.id_salesupply
                salesupply_row = salesupply_rows[id_salesupply]
                expected_qty = move.product_uom_qty
                delivered_qty = salesupply_row["ItemQuantityDelivered"]
                if expected_qty != delivered_qty:
                    logs |= log_object.log_info(_(f"The reception {picking.name} is not yet delivered to Salesupply"))
                    is_delivered = False
            if is_delivered:
                logs |= log_object.log_info(_(f"The reception {picking.name} is now delivered"))
                delivered_receptions |= picking

        delivered_receptions.button_validate()
        delivered_receptions.salesupply_synchronized = True
        return logs
    