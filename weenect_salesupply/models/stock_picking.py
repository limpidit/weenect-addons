
from odoo import models, fields, api, _

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
        
        salesupply_date_done = salesupply_data['DateReceived']
        date_done = parser.isoparse(salesupply_date_done) if salesupply_date_done else False
        
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
                picking.button_validate(date_done)
                picking.salesupply_synchronized = True
                log_object.log_info(_(f"The reception {picking.name} is now delivered"))
        
    @api.model
    def _return_pickings_from_salesupply(self, salesupply_returns):
        log_object = self.env['salesupply.log']
        
        for salesupply_json_return in salesupply_returns:
            return_code = salesupply_json_return['ReturnCode']
            
            salesupply_date_done = salesupply_json_return['ReceivedDate']
            date_done = parser.isoparse(salesupply_date_done) if salesupply_date_done else False
            
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
                backorder.button_validate(date_done)
                backorder.write({'salesupply_synchronized': True, 'salesupply_code': return_code})
                log_object.log_info(title=_(f"{backorder.name} Backorder created from {delivery.name}"))
                    
            except Exception as exception:
                log_object.log_error(title=_(f"Error while returning {return_code}"), message=str(exception))

    @api.model
    def _create_shipments_from_salesupply(self, salesupply, shop, warehouse, salesupply_shipments):
        log_object = self.env['salesupply.log']
        lot_object = self.env['stock.lot']
        move_line_object = self.env['stock.move.line']
        shop_product_object = self.env['salesupply.shop.product']
        
        for salesupply_json_shipment in salesupply_shipments[warehouse.id_salesupply]:
            shipment_code = salesupply_json_shipment['ShippingCode']
            
            salesupply_date_done = salesupply_json_shipment['ShippedTimestamp']
            date_done = parser.isoparse(salesupply_date_done) if salesupply_date_done else False
            
            # There should no be already synchronized shipments in the API response
            existing_delivery = self.search([('salesupply_code', '=', shipment_code), ('salesupply_synchronized', '=', True)])
            if existing_delivery:
                log_object.log_warning(title=_(f"Trying to confirm already shipped delivery {shipment_code}"))
                continue
            
            try:
                new_shipment = self.create({
                    'origin': salesupply_json_shipment['OrderCode'],
                    'salesupply_order_id': salesupply_json_shipment['OrderId'],
                    'partner_id': shop.shippings_default_customer_id.id,
                    'picking_type_id': warehouse.out_type_id.id,
                    'salesupply_synchronized': True,
                    'salesupply_code': shipment_code,
                })
                
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

                    move_line_vals.append({
                        'picking_id': new_shipment.id,
                        'product_id': product_id,
                        'lot_id': lot_id.id if lot_id else False,
                        'qty_done': row['ItemQuantity'],
                    })
                    
                move_line_object.create(move_line_vals)
                new_shipment.button_validate(date_done)
                log_object.log_info(title=_(f"Successfully delivered {shipment_code} -> {new_shipment.name}"))

            except Exception as e:
                log_object.log_error(title=_(f"Error creating delivery {shipment_code}"), message=str(e))

    def button_validate(self, date_done=None):
        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)

        # Sanity checks.
        if not self.env.context.get('skip_sanity_check', False):
            self._sanity_check()

        self.message_subscribe([self.env.user.partner_id.id])

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        pickings_not_to_backorder = self.filtered(lambda p: p.picking_type_id.create_backorder == 'never')
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder |= self.browse(self.env.context['picking_ids_not_to_backorder']).filtered(
                lambda p: p.picking_type_id.create_backorder != 'always'
            )
        pickings_to_backorder = self - pickings_not_to_backorder
        
        # LIMPIDIT Override here
        pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done(date_done)
        pickings_to_backorder.with_context(cancel_backorder=False)._action_done(date_done)

        if self.user_has_groups('stock.group_reception_report'):
            pickings_show_report = self.filtered(lambda p: p.picking_type_id.auto_show_reception_report)
            lines = pickings_show_report.move_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity_done and not m.move_dest_ids)
            if lines:
                # don't show reception report if all already assigned/nothing to assign
                wh_location_ids = self.env['stock.location']._search([('id', 'child_of', pickings_show_report.picking_type_id.warehouse_id.view_location_id.ids), ('usage', '!=', 'supplier')])
                if self.env['stock.move'].search([
                        ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
                        ('product_qty', '>', 0),
                        ('location_id', 'in', wh_location_ids),
                        ('move_orig_ids', '=', False),
                        ('picking_id', 'not in', pickings_show_report.ids),
                        ('product_id', 'in', lines.product_id.ids)], limit=1):
                    action = pickings_show_report.action_view_reception_report()
                    action['context'] = {'default_picking_ids': pickings_show_report.ids}
                    return action
        return True
                
    def _action_done(self, date_done=None):
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
        self.write({'date_done': date_done if date_done else fields.Datetime.now(), 'priority': '0'})

        # if incoming/internal moves make other confirmed/partially_available moves available, assign them
        done_incoming_moves = self.filtered(lambda p: p.picking_type_id.code in ('incoming', 'internal')).move_ids.filtered(lambda m: m.state == 'done')
        done_incoming_moves._trigger_assign()

        self._send_confirmation_email()
        return True