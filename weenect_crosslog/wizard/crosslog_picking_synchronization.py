
from odoo import models, fields, Command, _
from odoo.exceptions import UserError, ValidationError

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
    sync_returns = fields.Boolean(string="Synchronize returns")

    def synchronize_deliveries(self):
        """Synchronize deliveries with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']

        warehouse = self.api_connection_id.warehouse_id
        partner = self.api_connection_id.default_delivery_partner_id
        shipping_status = self.api_connection_id.crosslog_order_state_ids
        unvalid_pickings_limit = float(self.api_connection_id.batch_threshold)

        try:
            log_object.log_info(title=_(f"Orders synchronization started."))
            deliveries = self.api_connection_id.process_get_customer_orders_updated_request()
            shipping_codes = {str(c) for c in shipping_status.mapped('code') if c is not None}
            unvalid_pickings = []

            for delivery in deliveries:
                try:
                    state = delivery.get('state')
                    order_number = delivery.get('order_number')
                    if not state:
                        unvalid_pickings.append(order_number)
                        log_object.log_warning(f"Delivery state is missing in the response for {order_number} order.")
                        continue
                    is_shipping = state in shipping_codes

                    picking = picking_object.search([
                        ('crosslog_code', '=', delivery.get('order_number')),
                        ('picking_type_id.code', '=', 'outgoing'),
                        ('location_id', '=', warehouse.lot_stock_id.id),
                        ('crosslog_synchronized', '=', True)
                    ], limit=1)

                    if is_shipping:
                        if picking:
                            if picking.state not in ['done', 'cancel']:
                                self.make_picking_ready(picking)
                                self.validate_picking(picking)
                        else:
                            new_picking = self.create_delivery(delivery, warehouse, partner, picking_object)
                            if new_picking:
                                self.make_picking_ready(new_picking)
                                self.validate_picking(new_picking)
                            else:
                                unvalid_pickings.append(order_number)
                    else:
                        if picking:
                            continue
                        else:
                            new_picking = self.create_delivery(delivery, warehouse, partner, picking_object)
                            if new_picking:
                                self.make_picking_ready(new_picking)
                            else:
                                unvalid_pickings.append(order_number)
                
                except Exception as e:
                    log_object.log_error(title=_(f"Error during {order_number} order synchronization."), message=_(e))
            
            log_object.log_info(title=_(f"Orders synchronization successfully completed."))

            self.batch_process(unvalid_pickings, unvalid_pickings_limit, deliveries, 'ValidateCustomerOrdersUpdated')

        except Exception as e:
            log_object.log_error(title=_(f"Error during orders synchronization."), message=_(e))


    def create_delivery(self, delivery, warehouse, partner, picking_object):
        product_product_object = self.env['product.product']
        lot_object = self.env['stock.lot']
        log_object = self.env['crosslog.log']

        move_line_vals = []
        no_error = True
        new_shipment = False
        for line in delivery.get('order_lines', []):
            sent_qty = line.get('sent_qty' or 0.0)
            product = product_product_object.search([('default_code', '=', line['code'])], limit=1)
            if not product:
                log_object.log_warning(title=_(f"The product {line['code']} does not exist in Odoo."))
                no_error = False
                continue
            
            if product.tracking == 'lot':
                lots = line.get('lots')
                if lots:
                    for lot in lots:
                        lot_code = (lot.get('lot_code') or '').strip()
                        exist_lot = lot_object.search([('name', '=', lot_code), ('product_id', '=', product.id)], limit=1)
                        qty = qty = float(lot.get('quantity') or 0.0)
                        if not exist_lot:
                            exist_lot = lot_object.create({
                                'name': lot_code, 
                                'product_id': product.id, 
                                'is_default_crosslog_lot': True,
                                'available_on_crosslog': True
                            })
                        move_line_vals.append(Command.create({
                            'product_id': product.id,
                            'lot_id': exist_lot.id if exist_lot else False,
                            'qty_done': qty,
                        }))
                else:
                    log_object.log_warning(title=_(f"Product {line['code']} managed without lot in Crosslog while managed with lot in Odoo for order {delivery.get('order_number')}."))
                    no_error = False
                    continue
            else:
                move_line_vals.append(Command.create({
                    'product_id': product.id,
                    'qty_done': sent_qty,
                }))
        
        if no_error:
            new_shipment = picking_object.create({
                'partner_id': partner.id,
                'picking_type_id': warehouse.out_type_id.id,
                'crosslog_synchronized': True,
                'crosslog_code': delivery.get('order_number'),
                'move_line_ids_without_package': move_line_vals,
            })
        return new_shipment

    def synchronize_receptions(self):
        """Synchronize receptions with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']
        product_product_object = self.env['product.product']
        move_object = self.env['stock.move']

        warehouse = self.api_connection_id.warehouse_id
        arrival_status = self.api_connection_id.crosslog_reception_state_ids
        unvalid_pickings_limit = float(self.api_connection_id.batch_threshold)

        try:
            log_object.log_info(title=_("Receptions synchronization started."))
            receptions = self.api_connection_id.process_get_supplier_orders_updated_request()
            arrival_codes = {str(c) for c in arrival_status.mapped('code') if c is not None}
            unvalid_pickings = []

            for reception in receptions:
                try:
                    skip_reception = False
                    state = reception.get('state')
                    order_number = reception.get('order_number')
                    if not state:
                        log_object.log_warning(_(f"Reception state is missing in the response for {order_number} reception."))
                        continue
                    if not order_number:
                        log_object.log_warning(_(f"Reception order number is missing in the response."))
                        continue
                    is_arrived = state in arrival_codes

                    if is_arrived:
                        picking = picking_object.search([
                            ('origin', '=', order_number),
                            ('picking_type_id.code', '=', 'internal'),
                            ('location_dest_id', '=', warehouse.lot_stock_id.id),
                            ('crosslog_synchronized', '=', False),
                            ('state', '=', 'assigned')
                        ], limit=1)
                        if not picking:
                            unvalid_pickings.append(order_number)
                            log_object.log_warning(_(f"No {order_number} reception found in Odoo."))
                            continue

                        lines = reception.get('order_lines') or []
                        if not lines:
                            log_object.log_warning(_(f"No order lines from Crosslog for {order_number} reception."))
                            continue

                        for line in lines:
                            product = product_product_object.search([('default_code', '=', line['code'])], limit=1)
                            receipt_qty = float(line.get('receipt_qty') or 0.0)
                            initial_qty = float(line.get('initial_qty') or 0.0)
                            if not product:
                                skip_reception = True
                                unvalid_pickings.append(order_number)
                                log_object.log_warning(_(f"No product {line['code']} found in Odoo for {order_number} reception."))
                                break

                            move = picking.move_ids.filtered(lambda m: m.product_id.id == product.id)
                            if move:
                                move._action_confirm()
                                move._do_unreserve()
                                move.product_uom_qty = max(receipt_qty, move.product_uom_qty or 0.0)
                                move._action_assign()

                                remaining = self._allocate_qty_on_move_lines(move, receipt_qty)
                                if remaining > 0:
                                    skip_reception = True
                                    unvalid_pickings.append(order_number)
                                    log_object.log_warning(_(f"{order_number}: validation blocked (incomplete lot allocation)."))
                                    break
                            else:
                                move_vals = {
                                    'name': product.name,
                                    'product_id': product.id,
                                    'product_uom_qty': initial_qty,
                                    'reserved_availability': initial_qty,
                                    'quantity_done': receipt_qty,
                                    'picking_id': picking.id,
                                    'location_id': picking.location_id.id,
                                    'location_dest_id': picking.location_dest_id.id,
                                }
                                move_object.create(move_vals)
                                log_object.log_info(title=_(f"New line created on transfer {picking.name} with product {product.name}."))

                        if skip_reception:
                            continue

                        try:
                            self.make_picking_ready(picking)
                            self.validate_picking(picking)

                            picking.crosslog_synchronized = True
                            picking.crosslog_code = order_number
                        except Exception as e:
                            log_object.log_warning(title=_(f"{picking.name}: validation skipped", message=(e)))
                            continue

                except Exception as e:
                    log_object.log_error(
                        title=_(f"Error during {order_number} reception synchronization."),
                        message=(e)
                    )

            log_object.log_info(title=_("Receptions synchronization successfully completed."))

            self.batch_process(unvalid_pickings, unvalid_pickings_limit, receptions, 'ValidateSupplierOrdersUpdated')

        except Exception as e:
            log_object.log_error(title=_("Error during receptions synchronization."), message=(e))


    def _allocate_qty_on_move_lines(self, move, receipt_qty):
        """Répartit receipt_qty sur les SML du move en respectant le tracking/lot."""
        log_object = self.env['crosslog.log']

        remaining = float(receipt_qty or 0.0)
        if remaining <= 0:
            return 0.0

        product = move.product_id
        mls = move.move_line_ids

        if product.tracking == 'none':
            ml = mls[:1]
            if not ml:
                ml = self.env['stock.move.line'].create({
                    'move_id': move.id,
                    'product_id': product.id,
                    'product_uom_id': move.product_uom.id,
                    'picking_id': move.picking_id.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'reserved_uom_qty': 0.0,
                })
            ml.write({
                'qty_done': remaining,
                'reserved_uom_qty': max(ml.reserved_uom_qty, remaining),
            })
            return 0.0

        mls = mls.sorted(key=lambda l: (-(l.reserved_uom_qty or 0.0), l.id))

        for ml in mls:
            if remaining <= 0:
                break
            reserved = float(ml.reserved_uom_qty or 0.0)
            done = float(ml.qty_done or 0.0)
            capacity = max(reserved - done, 0.0)
            if capacity <= 0:
                capacity = 0.0
            alloc = min(remaining, capacity) if capacity > 0 else 0.0
            if alloc > 0:
                ml.qty_done = done + alloc
                remaining -= alloc

        if remaining > 0:
            lot_ids = mls.mapped('lot_id').ids
            lot_ids = [lid for lid in lot_ids if lid]
            unique_lot = len(set(lot_ids)) == 1 and len(lot_ids) >= 1
            if unique_lot:
                last_ml = mls[-1]
                last_ml.qty_done = float(last_ml.qty_done or 0.0) + remaining
                remaining = 0.0
            else:
                log_object.log_warning(_(
                    f"Unable to allocate {remaining} {product.name} across multiple lots"
                ))

        return remaining


    def synchronize_returns(self):
        """Synchronize returns with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']
        product_product_object = self.env['product.product']
        move_object = self.env['stock.move']
        move_line_object = self.env['stock.move.line']

        warehouse = self.api_connection_id.warehouse_id
        return_status = self.api_connection_id.crosslog_return_state_ids
        unvalid_pickings_limit = float(self.api_connection_id.batch_threshold)

        try:
            log_object.log_info(title=_(f"Returns synchronization started."))
            returns = self.api_connection_id.process_get_customer_returns_updated_request()
            return_codes = {str(c) for c in return_status.mapped('code') if c is not None}
            valid_returns = [
                re for re in returns
                if re.get('state') in return_codes
            ]
            unvalid_pickings = []

            for re in valid_returns:
                try:
                    return_number = re.get('return_number') or []
                    order_number = re.get('order_number') or []
                    lines = re.get('order_lines') or []

                    if not return_number:
                        log_object.log_warning(f"Return number is missing in the response.")
                        unvalid_pickings.append("Unknow")
                        continue
                    if not order_number:
                        log_object.log_warning(f"Order number is missing in the response for {return_number} return.")
                        unvalid_pickings.append(return_number)
                        continue
                    if not lines:
                        log_object.log_warning(f"No order lines from Crosslog for {return_number} return.")
                        unvalid_pickings.append(return_number)
                        continue
                    
                    exist_return = picking_object.search([
                        ('crosslog_code', '=', return_number),
                        ('picking_type_id.code', '=', 'incoming'),
                        ('location_dest_id', '=', warehouse.lot_stock_id.id),
                        ('crosslog_synchronized', '=', True)
                    ])
                    if exist_return:
                        log_object.log_info(f"Return {return_number} already exist in Odoo.")
                        continue

                    delivery = picking_object.search([
                        ('crosslog_code', '=', order_number),
                        ('picking_type_id.code', '=', 'outgoing'),
                        ('location_id', '=', warehouse.lot_stock_id.id),
                        ('crosslog_synchronized', '=', True)
                    ], limit=1)

                    if not delivery:
                        log_object.log_warning(f"Synchronized delivery not found with {order_number} code for {return_number} return.")
                        unvalid_pickings.append(return_number)
                        continue

                    
                    return_picking = False
                    for line in lines:
                        receipt_qty = float(line['receipt_qty'] or 0.0)
                        if receipt_qty > 0:
                            product = product_product_object.search([('default_code', '=', line['code'])], limit=1)
                            if not product:
                                log_object.log_warning(f"Product {line['code']} not found in Odoo for {return_number} return.")
                                unvalid_pickings.append(return_number)
                                continue

                            move = delivery.move_ids.filtered(lambda m: m.product_id.id == product.id)
                            if not move:
                                log_object.log_warning(f"No line on {order_number} delivery with {line['code']} product matched for {return_number} return.")
                                unvalid_pickings.append(return_number)
                                continue
                            
                            if not return_picking:
                                return_type = delivery.picking_type_id.return_picking_type_id or delivery.picking_type_id
                                return_picking = picking_object.create({
                                    'picking_type_id': return_type.id,
                                    'company_id': delivery.company_id.id,
                                    'origin': f"Return of {delivery.name}",
                                    'partner_id': delivery.partner_id.id,
                                    'location_id': delivery.location_dest_id.id,
                                    'location_dest_id': delivery.location_id.id,
                                })

                            ret_move = move_object.create({
                                'name': move.name or product.display_name,
                                'product_id': product.id,
                                'product_uom_qty': receipt_qty,
                                'product_uom': move.product_uom.id,
                                'picking_id': return_picking.id,
                                'location_id': return_picking.location_id.id,
                                'location_dest_id': return_picking.location_dest_id.id,
                                'origin_returned_move_id': move.id,
                                'procure_method': 'make_to_stock',
                            })
                            ret_move._action_confirm()
                            ret_move._action_assign()

                            ml_vals = {
                                'move_id': ret_move.id,
                                'picking_id': return_picking.id,
                                'product_id': product.id,
                                'product_uom_id': move.product_uom.id,
                                'qty_done': receipt_qty,
                                'location_id': return_picking.location_id.id,
                                'location_dest_id': return_picking.location_dest_id.id,
                            }

                            if product.tracking in ('lot', 'serial'):
                                orig_ml = move.move_line_ids.filtered(lambda l: l.qty_done > 0)[:1]
                                if orig_ml.lot_id:
                                    ml_vals['lot_id'] = orig_ml.lot_id.id
                                elif orig_ml.lot_name:
                                    ml_vals['lot_name'] = orig_ml.lot_name

                            move_line_object.create(ml_vals)

                    return_picking.button_validate()

                    return_picking.crosslog_synchronized = True
                    return_picking.crosslog_code = return_number

                except Exception as e:
                    log_object.log_error(title=_(f"Error during {return_number} return synchronization."), message=(e))
            
            log_object.log_info(title=_(f"Returns synchronization successfully completed."))

            self.batch_process(unvalid_pickings, unvalid_pickings_limit, returns, 'ValidateCustomerReturnsUpdated')

        except Exception as e:
            log_object.log_error(title=_(f"Error during returns synchronization."), message=(e))


    def make_picking_ready(self, picking):
        picking.action_confirm()
        picking.action_assign()
            
    def validate_picking(self, picking):
        picking._action_done()
    
    def synchronize_pickings(self):
        """Synchronize pickings with Crosslog."""
        self.ensure_one()
        if not self.sync_deliveries and not self.sync_receptions and not self.sync_returns:
            raise UserError("Please select at least one synchronization option (deliveries, receptions or returns).")

        if self.sync_deliveries:
            self.synchronize_deliveries()

        if self.sync_receptions:
            self.synchronize_receptions()

        if self.sync_returns:
            self.synchronize_returns()

    def validate_batch(self, batch_name):
        if batch_name == 'ValidateSupplierOrdersUpdated':
            return self.api_connection_id.process_validate_suppplier_orders_updated_request()
        if batch_name == 'ValidateCustomerOrdersUpdated':
            return self.api_connection_id.process_validate_customer_orders_updated_request()
    
    def batch_process(self, unvalid_pickings, unvalid_pickings_limit, pickings, batch_name):
        details = ", ".join(unvalid_pickings) if unvalid_pickings else _("Nothing")
        picking_name = ""
        log_object = self.env['crosslog.log']

        if batch_name == 'ValidateSupplierOrdersUpdated':
            picking_name = "receptions"
        if batch_name == 'ValidateCustomerOrdersUpdated':
            picking_name = "deliveries"
        if batch_name == 'ValidateCustomerReturnsUpdated':
            picking_name = "returns"

        if len(unvalid_pickings) <= unvalid_pickings_limit:
            if len(pickings) > 0:
                result = self.validate_batch(batch_name)
                if result == 200:
                    log_object.log_info(
                        title=_(f"Batch validation successful. {len(unvalid_pickings)} {picking_name} were not validated."),
                        message=("Unvalidated %s (%s/%s): %s") % (picking_name, len(unvalid_pickings), len(pickings), details)
                    )
                    if batch_name == 'ValidateSupplierOrdersUpdated':
                        self.synchronize_receptions()
                    if batch_name == 'ValidateCustomerOrdersUpdated':
                        self.synchronize_deliveries()
                    if batch_name == 'ValidateCustomerReturnsUpdated':
                        self.synchronize_returns()
                else:
                    log_object.log_error(title=_(f"Batch validation failed with status code {result}."))
        else:
            log_object.log_warning(
                title=_(f"Batch validation skipped. {len(unvalid_pickings)} {picking_name} were not validated, exceeding the limit of {unvalid_pickings_limit}."),
                message=("Unvalidated %s (%s/%s): %s") % (picking_name, len(unvalid_pickings), len(pickings), details)
            )