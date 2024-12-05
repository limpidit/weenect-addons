
from odoo import models, fields, _

from ..models.salesupply_request import SalesupplyRequest


class SalesupplyShipmentSynchronization(models.TransientModel):
    _name = 'salesupply.shipment.synchronization'
    _description = "Synchronize deliveries shipped from Salesupply warehouses"

    shop_id = fields.Many2one(comodel_name='salesupply.shop', string="Shop", required=True,
        default=lambda self: self.env.context.get('default_shop_id'))
    warehouse_ids = fields.Many2many(comodel_name='stock.warehouse', relation='shipments_wiz_warehouse_rel',
        string="Warehouses to synchronize", required=True, domain="[('is_salesupply', '=', True), ('shop_id', '=', shop_id)]")
    date_from_synchronization = fields.Date(string="Date from wich pickings should be synchronized")
    
    def synchronize_shipments(self):
        picking_object = self.env['stock.picking']
        location_object = self.env['stock.location']
        shop_product_object = self.env['salesupply.shop.product']
        log_object = self.env['salesupply.log']
        logs = log_object
        
        salesupply = SalesupplyRequest(self.shop_id.connection_id)
        
        for warehouse in self.warehouse_ids:
            salesupply_shipments = salesupply._get_shipments(warehouse.id_salesupply, self.date_from_synchronization)
            
            if 'error_message' in salesupply_shipments:
                logs |= log_object.log_error(title=_("Error while retrieving shipments"), message=salesupply_shipments['error_message'])
                continue
            logs |= log_object.log_info(title=_(f"Starting synchronization of {warehouse.name} shipments"), message=salesupply_shipments)
            
            for salesupply_json_shipment in salesupply_shipments:
                shipping_salesupply_code = salesupply_json_shipment['ShippingCode']
                shipping_salesupply_id = salesupply_json_shipment['Id']
                shipping_salesupply_order_id = salesupply_json_shipment['OrderId']
                
                existing_shipment = picking_object.search([
                    ('tracking_number', '=', shipping_salesupply_code),
                ])
                
                if len(existing_shipment) > 1:
                    logs |= log_object.log_warning(title=_(f"More than 1 shipment found for the code {shipping_salesupply_code}"))
                    continue
                
                if not existing_shipment:
                    shipment_details = salesupply._get_shipment_details(shipping_salesupply_id)
                    shipping_salesupply_order_rows = shipment_details['OrderRows']
                    order_rows = salesupply._get_order_rows(shipping_salesupply_order_id)
                    shipment_rows = filter(lambda r: r['Id'] in shipping_salesupply_order_rows, order_rows)
                    picking_vals = {
                        'partner_id': self.shop_id.shippings_default_customer_id.id,
                        'picking_type_id': warehouse.out_type_id.id,
                        'tracking_number': shipping_salesupply_code,
                        'salesupply_synchronized': True
                    }
                    moves = []
                    for row in shipment_rows:
                        shop_product = shop_product_object.search([('id_salesupply', '=', row['ProductId'])])
                        if not shop_product:
                            logs |= log_object.log_warning(title=_(f"Product not found in Odoo {row['ProductCode']}"))
                            continue
                        customer_location = location_object.search([('usage', '=', 'customer')], limit=1)
                        moves.append((0, 0, {
                            'product_id': shop_product.product_tmpl_id.product_variant_id.id,
                            'name': shop_product.product_tmpl_id.name,
                            'product_uom_qty': int(row['ItemQuantity']),
                            'location_id': warehouse.lot_stock_id.id,
                            'location_dest_id': customer_location.id,
                        }))
                    picking_vals['move_ids_without_package'] = moves
                    existing_shipment = picking_object.create(picking_vals)
                    existing_shipment.action_confirm()
                    logs |= log_object.log_info(title=_(f"New shipment created {existing_shipment.name}"))
                    
                if existing_shipment and salesupply_json_shipment['ShippedTimestamp'] and existing_shipment.state == 'assigned':
                    try:
                        existing_shipment.button_validate()
                        existing_shipment.salesupply_shipped = True
                        logs |= log_object.log_info(title=_(f"Shipment {existing_shipment.name} is now done"))
                    except Exception as exception:
                        logs |= log_object.log_error(title=_("Couldnt validate picking"), message=str(exception))

        return {
            'type': 'ir.actions.act_window',
            'name': "Synchronization of receptions",
            'view_mode': 'tree,form',
            'res_model': 'salesupply.log',
            'target': 'new',
            'id': self.env.ref('weenect_salesupply.salesupply_log_action').id,
            'context': {'create': False},
            'domain': [('id', 'in', logs.ids)]
        }