
from odoo import models, Command, fields, api, _

from dateutil import parser


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    salesupply_code = fields.Char(string="Salesupply code")
    salesupply_order_id = fields.Char(string="Salesupply order id")
    salesupply_synchronized = fields.Boolean(string="Synchronized with Salesupply", default=False, copy=False)
    is_transfered_to_salesupply = fields.Boolean(compute='_compute_salesupply_picking_type', store=True)
    is_delivered_from_salesupply = fields.Boolean(compute='_compute_salesupply_picking_type', store=True)
    is_returned_to_salesupply = fields.Boolean(compute='_compute_salesupply_picking_type', store=True)
    
    @api.depends('location_id', 'location_dest_id', 'picking_type_id')
    def _compute_salesupply_picking_type(self):
        salesupply_warehouses = self.env['stock.warehouse'].search([('is_salesupply', '=', True)])
        for record in self:
            if record.location_dest_id.id in salesupply_warehouses.mapped('lot_stock_id.id') and record.picking_type_id.code == 'internal':
                record.is_transfered_to_salesupply = True
                record.is_delivered_from_salesupply = False
                record.is_returned_to_salesupply = False
            elif record.location_id.id in salesupply_warehouses.mapped('lot_stock_id.id') and record.picking_type_id.code == 'outgoing':
                record.is_transfered_to_salesupply = False
                record.is_delivered_from_salesupply = True
                record.is_returned_to_salesupply = False
            elif record.location_dest_id.id in salesupply_warehouses.mapped('lot_stock_id.id') and record.picking_type_id.code == 'incoming':
                record.is_transfered_to_salesupply = False
                record.is_delivered_from_salesupply = False
                record.is_returned_to_salesupply = True
            else:
                record.is_transfered_to_salesupply = False
                record.is_delivered_from_salesupply = False
                record.is_returned_to_salesupply = False
        
    def _validate_internal_transfer_from_salesupply(self, salesupply_data):
        log_object = self.env['salesupply.log']
        
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
                salesupply_date_done = salesupply_data['DateReceived']
                date_done = parser.isoparse(salesupply_date_done) if salesupply_date_done else False
                picking.with_context(shipping_date_done=date_done).button_validate()
                picking.salesupply_synchronized = True
                log_object.log_info(_(f"The reception {picking.name} is now delivered"))
        
    @api.model
    def _return_pickings_from_salesupply(self, salesupply_returns):
        log_object = self.env['salesupply.log']
        
        for salesupply_json_return in salesupply_returns:
            return_code = salesupply_json_return['ReturnCode']
            
            try:
                existing_return = self.search([('salesupply_code', '=', return_code), ('salesupply_synchronized', '=', True)])
                if existing_return:
                    raise ValueError(f"Already returned {return_code}")
            
                delivery = self.search([('salesupply_order_id', '=', salesupply_json_return['OrderId'])])
                
                if not delivery:
                    log_object.log_warning(title=_(f"Could not synchronize return {return_code} because of missing delivery"))
                    continue
                
                return_wizard = self.env['stock.return.picking'].with_context({'active_id': delivery.id, 'active_model': 'stock.picking'}).create({})
                return_wizard._onchange_picking_id()
            
                for return_row in salesupply_json_return['OrderReturnRows']:
                    line = return_wizard.product_return_moves.filtered(lambda m, return_row=return_row: m.product_id.default_code == return_row['ProductCode'])
                    line.quantity = return_row['ReturnedQuantity']
                    
                backorder_id = return_wizard._create_returns()[0]
                backorder = self.browse(backorder_id)
                backorder.move_ids._set_quantities_to_reservation()
                salesupply_date_done = salesupply_json_return['ReceivedDate']
                date_done = parser.isoparse(salesupply_date_done) if salesupply_date_done else False
                backorder.with_context(shipping_date_done=date_done).button_validate()
                backorder.write({'salesupply_synchronized': True, 'salesupply_code': return_code})
                log_object.log_info(title=_(f"{backorder.name} Backorder created from {delivery.name}"))
                    
            except Exception as exception:
                log_object.log_error(title=_(f"Error while returning {return_code}"), message=str(exception))

    @api.model
    def _create_shipments_from_salesupply(self, salesupply, shop, warehouse, salesupply_shipments):
        log_object = self.env['salesupply.log']
        lot_object = self.env['stock.lot']
        shop_product_object = self.env['salesupply.shop.product']
        
        for salesupply_json_shipment in salesupply_shipments[warehouse.id_salesupply]:
            shipment_code = salesupply_json_shipment['ShippingCode']
            
            # There should no be already synchronized shipments in the API response
            existing_delivery = self.search([('salesupply_code', '=', shipment_code), ('salesupply_synchronized', '=', True)])
            if existing_delivery:
                log_object.log_warning(title=_(f"Trying to confirm already shipped delivery {shipment_code}"))
                continue
            
            try:
                
                detailled_rows = salesupply._get_shipment_rows(salesupply_json_shipment['OrderRows'], salesupply_json_shipment['OrderId'])

                move_line_vals = []
                for row in detailled_rows:
                    shop_product = shop_product_object.search([('id_salesupply', '=', row['ProductId'])], limit=1)

                    if not shop_product:
                        raise ValueError(f"Product with Salesupply ID {row['ProductId']} not found in shop {shop.name}")

                    product_id = shop_product.product_tmpl_id.product_variant_id.id

                    lot_id = False
                    if shop_product.product_tmpl_id.tracking == 'lot':
                        lot_id = lot_object.search([('product_id', '=', product_id), ('is_default_salesupply_lot', '=', True)], limit=1)
                        if not lot_id:
                            lot_id = lot_object.create({
                                'name': shop.default_lot_name, 
                                'product_id': product_id, 
                                'is_default_salesupply_lot': True
                            })
                    
                    move_line_vals.append(Command.create({
                        'product_id': product_id,
                        'lot_id': lot_id.id if lot_id else False,
                        'quantity': row['ItemQuantity'],
                    }))

                new_shipment = self.create({
                    'origin': salesupply_json_shipment['OrderCode'],
                    'salesupply_order_id': salesupply_json_shipment['OrderId'],
                    'partner_id': shop.shippings_default_customer_id.id,
                    'picking_type_id': warehouse.out_type_id.id,
                    'salesupply_synchronized': True,
                    'salesupply_code': shipment_code,
                    'move_line_ids': move_line_vals,
                })

                salesupply_date_done = salesupply_json_shipment['ShippedTimestamp']
                date_done = parser.isoparse(salesupply_date_done) if salesupply_date_done else False
                new_shipment.with_context(shipping_date_done=date_done).button_validate()
                log_object.log_info(title=_(f"Successfully delivered {shipment_code} -> {new_shipment.name}"))

            except Exception as e:
                log_object.log_error(title=_(f"Error creating delivery {shipment_code}"), message=str(e))

    def _action_done(self):
        """Call `_action_done` on the `stock.move` of the `stock.picking` in `self`.
        This method makes sure every `stock.move.line` is linked to a `stock.move` by either
        linking them to an existing one or a newly created one.

        If the context key `cancel_backorder` is present, backorders won't be created.

        :return: True
        :rtype: bool
        """
        self._check_company()

        todo_moves = self.move_ids.filtered(lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
        for picking in self:
            if picking.owner_id:
                picking.move_ids.write({'restrict_partner_id': picking.owner_id.id})
                picking.move_line_ids.write({'owner_id': picking.owner_id.id})
        todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
        
        # LIMPIDIT Override here
        salesupply_date_done = self.env.context.get('salesupply_date_done')
        self.write({'date_done': salesupply_date_done if salesupply_date_done else fields.Datetime.now(), 'priority': '0'})

        # if incoming/internal moves make other confirmed/partially_available moves available, assign them
        done_incoming_moves = self.filtered(lambda p: p.picking_type_id.code in ('incoming', 'internal')).move_ids.filtered(lambda m: m.state == 'done')
        done_incoming_moves._trigger_assign()

        self._send_confirmation_email()
        return True