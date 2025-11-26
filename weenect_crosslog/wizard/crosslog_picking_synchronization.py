
from odoo import models, fields, _
from odoo.exceptions import UserError

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
        unvalid_pickings_limit = float(self.api_connection_id.batch_threshold or 5)

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
                        log_object.log_warning(title=_("Delivery state is missing in the response for Crosslog order %s.") % (order_number))
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
                                if not picking.try_make_picking_ready(order_number):
                                    unvalid_pickings.append(order_number)
                                    continue
                                if not picking.try_validate_picking(order_number):
                                    unvalid_pickings.append(order_number)
                                    continue
                        else:
                            new_picking = picking_object.create_delivery(delivery, warehouse, partner)
                            if new_picking:
                                if not new_picking.try_make_picking_ready(order_number):
                                    unvalid_pickings.append(order_number)
                                    continue
                                if not new_picking.try_validate_picking(order_number):
                                    unvalid_pickings.append(order_number)
                                    continue
                            else:
                                unvalid_pickings.append(order_number)
                
                except Exception as e:
                    log_object.log_error(title=_("Error during synchronisation of Crosslog order %s.") % (order_number), message=str(e))
            
            log_object.log_info(title=_(f"Orders synchronization successfully completed."))
        
            # self.batch_process(unvalid_pickings, unvalid_pickings_limit, deliveries, 'ValidateCustomerOrdersUpdated')

        except Exception as e:
            log_object.log_error(title=_(f"Error during orders synchronization."), message=str(e))


    def synchronize_receptions(self):
        """Synchronize receptions with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']
        product_product_object = self.env['product.product']

        warehouse = self.api_connection_id.warehouse_id
        arrival_status = self.api_connection_id.crosslog_reception_state_ids
        unvalid_pickings_limit = float(self.api_connection_id.batch_threshold)

        try:
            log_object.log_info(title=_(f"Receptions synchronization started."))
            receptions = self.api_connection_id.process_get_supplier_orders_updated_request()
            arrival_codes = {str(c) for c in arrival_status.mapped('code') if c is not None}
            unvalid_pickings = []

            for reception in receptions:
                try:
                    skip_reception = False
                    state = reception.get('state')
                    order_number = reception.get('order_number')

                    if not state:
                        log_object.log_warning(title=_("Reception state is missing in the response for Crosslog reception number %s.") % (order_number))
                        continue
                    if not order_number:
                        log_object.log_warning(title=_(f"Reception order number is missing in the response."))
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
                            picking_synchronized = picking_object.search([
                                ('origin', '=', order_number),
                                ('picking_type_id.code', '=', 'internal'),
                                ('location_dest_id', '=', warehouse.lot_stock_id.id),
                                ('crosslog_synchronized', '=', True),
                                ('state', '=', 'done')
                            ], limit=1)
                            if not picking_synchronized:
                                unvalid_pickings.append(order_number)
                                log_object.log_warning(title=_("Reception with Crosslog code %s not found in Odoo or already validated.") % (order_number))
                                continue
                            else:
                                log_object.log_info(title=_("Reception with Crosslog code %s already validated.") % (order_number))
                                continue

                        lines = reception.get('order_lines') or []
                        if not lines:
                            unvalid_pickings.append(order_number)
                            log_object.log_warning(title=_("Reception %s not validated.") % (picking.name), message=_("No order lines from Crosslog.\nCrosslog origin : %s.") % (order_number))
                            continue

                        for line in lines:
                            product_code = line['code']
                            product = product_product_object.search([('default_code', '=', product_code), ('available_on_crosslog', '=', True)], limit=1)
                            receipt_qty = float(line.get('receipt_qty') or 0.0)
                            
                            if not product:
                                skip_reception = True
                                unvalid_pickings.append(order_number)
                                log_object.log_warning(title=_("Reception %s not validated.") % (picking.name), message=_("The product %s does not exist in Odoo or is not synchronised with Crosslog.\nCrosslog origin : %s.") % (product_code, order_number))
                                break
                            
                            move = picking.move_ids.filtered(lambda m: m.product_id.id == product.id)
                            if move:
                                expected_qty = move.product_uom_qty
                                if expected_qty != receipt_qty:
                                    skip_reception = True
                                    unvalid_pickings.append(order_number)
                                    log_object.log_warning(title=_("Reception %s not validated.") % (picking.name), message=_("Quantity mismatch for product %s.\nExpected quantity in Odoo : %s. Received quantity in Crosslog : %s.\nCrosslog origin : %s.") % (product.name, expected_qty, receipt_qty, order_number))
                                    break
                            
                                move._action_confirm()
                                move._action_assign()

                            else:
                                skip_reception = True
                                unvalid_pickings.append(order_number)
                                log_object.log_warning(title=_("Reception %s not validated.") % (picking.name), message=_("No line on transfer %s with product %s matched.\nCrosslog origin : %s.") % (picking.name, product_code, order_number))
                                break

                        if skip_reception:
                            continue

                        if not picking.try_make_picking_ready(order_number):
                            unvalid_pickings.append(order_number)
                            continue
                        if not picking.try_validate_picking(order_number):
                            unvalid_pickings.append(order_number)
                            continue

                        picking.crosslog_synchronized = True
                        picking.crosslog_code = order_number

                except Exception as e:
                    log_object.log_error(
                        title=_("Error during synchronization of Crosslog reception %s.") % (order_number),
                        message=str(e)
                    )

            log_object.log_info(title=_(f"Receptions synchronization successfully completed."))

            self.batch_process(unvalid_pickings, unvalid_pickings_limit, receptions, 'ValidateSupplierOrdersUpdated')

        except Exception as e:
            log_object.log_error(title=_(f"Error during receptions synchronization."), message=str(e))

    def synchronize_returns(self):
        """Synchronize returns with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']

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
                        log_object.log_warning(title=_(f"Return number is missing in the response."))
                        unvalid_pickings.append("Unknow")
                        continue
                    if not order_number:
                        log_object.log_warning(title=_("Return %s not synchronized") % (return_number), message=_(f"Order number is missing in the response."))
                        unvalid_pickings.append(return_number)
                        continue
                    if not lines:
                        log_object.log_warning(title=_("Return %s not synchronized") % (return_number), message=_(f"No order lines from Crosslog"))
                        unvalid_pickings.append(return_number)
                        continue
                    
                    exist_return = picking_object.search([
                        ('crosslog_code', '=', return_number),
                        ('picking_type_id.code', '=', 'incoming'),
                        ('location_dest_id', '=', warehouse.lot_stock_id.id),
                        ('crosslog_synchronized', '=', True)
                    ])
                    if exist_return:
                        log_object.log_info(title=_("Return %s is already synchronized in Odoo.") % (return_number))
                        continue

                    delivery = picking_object.search([
                        ('crosslog_code', '=', order_number),
                        ('picking_type_id.code', '=', 'outgoing'),
                        ('location_id', '=', warehouse.lot_stock_id.id),
                        ('crosslog_synchronized', '=', True),
                        ('state', '=', 'done')
                    ], limit=1)

                    if not delivery:
                        log_object.log_warning(title=_("Return %s not synchronized") % (return_number), message=_("Synchronized done delivery %s not found in Odoo.") % (order_number))
                        unvalid_pickings.append(return_number)
                        continue

                    return_picking = picking_object.create_return(lines, return_number, order_number, delivery)
                    if not return_picking:
                        unvalid_pickings.append(return_number)
                        continue
                    
                    if not return_picking.try_validate_picking(return_number):
                        unvalid_pickings.append(return_number)
                        continue

                    return_picking.crosslog_synchronized = True
                    return_picking.crosslog_code = return_number

                except Exception as e:
                    log_object.log_error(title=_("Error during synchronization of return %s.") % (return_number), message=str(e))
            
            log_object.log_info(title=_(f"Returns synchronization successfully completed."))

            self.batch_process(unvalid_pickings, unvalid_pickings_limit, returns, 'ValidateCustomerReturnsUpdated')

        except Exception as e:
            log_object.log_error(title=_(f"Error during returns synchronization."), message=str(e))

    
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
        if batch_name == 'ValidateCustomerReturnsUpdated':
            return self.api_connection_id.process_validate_customer_returns_updated_request()
    
    def batch_process(self, unvalid_pickings, unvalid_pickings_limit, pickings, batch_name):
        details = ", ".join(unvalid_pickings) if unvalid_pickings else _("Nothing")
        picking_name = ""
        log_object = self.env['crosslog.log']

        if batch_name == 'ValidateSupplierOrdersUpdated':
            picking_name = "commandes fournisseurs"
        if batch_name == 'ValidateCustomerOrdersUpdated':
            picking_name = "commandes clients"
        if batch_name == 'ValidateCustomerReturnsUpdated':
            picking_name = "retours"

        if len(unvalid_pickings) <= unvalid_pickings_limit:
            if len(pickings) > 0:
                result = self.validate_batch(batch_name)
                if result == 200:
                    log_object.log_info(
                        title=_("Batch validation successful. %s %s were not validated.") % (len(unvalid_pickings), picking_name),
                        message=_("Unvalidated %s (%s/%s): %s") % (picking_name, len(unvalid_pickings), len(pickings), details)
                    )
                    if batch_name == 'ValidateSupplierOrdersUpdated':
                        self.synchronize_receptions()
                    if batch_name == 'ValidateCustomerOrdersUpdated':
                        self.synchronize_deliveries()
                    if batch_name == 'ValidateCustomerReturnsUpdated':
                        self.synchronize_returns()
                else:
                    log_object.log_error(title=_("Batch validation failed with status code %s.") % (result))
        else:
            log_object.log_warning(
                title=_("Batch validation skipped. %s %s were not validated, exceeding the limit of %s.") % (len(unvalid_pickings), picking_name, round(unvalid_pickings_limit)),
                message=_("Unvalidated %s (%s/%s): %s") % (picking_name, len(unvalid_pickings), len(pickings), details)
            )