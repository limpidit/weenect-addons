
from odoo import models, fields, Command, _
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

    def synchronize_deliveries(self):
        """Synchronize deliveries with Crosslog."""
        print('')
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']

        warehouse = self.api_connection_id.warehouse_id
        partner = self.api_connection_id.default_delivery_partner_id
        shipping_status = self.api_connection_id.crosslog_order_state_ids

        try:
            log_object.log_info(title=_(f"Orders synchronization started."))
            deliveries = self.api_connection_id.process_get_customer_orders_updated_request()
            shipping_codes = {str(c) for c in shipping_status.mapped('code') if c is not None}
            #Gérer les batchs
            for delivery in deliveries:
                try:
                    state = delivery.get('state')
                    if not state:
                        log_object.log_warning(f"Delivery state is missing in the response for {delivery.get('order_number')} order.")
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
                            if picking.state != 'done':
                                picking.action_confirm()
                                picking.action_assign()
                                picking._action_done()
                        else:
                            new_picking = self.create_delivery(delivery, warehouse, partner, picking_object)
                            if new_picking:
                                self.make_picking_ready(new_picking)
                                self.validate_picking(new_picking)
                    else:
                        if picking:
                            continue
                        else:
                            new_picking = self.create_delivery(delivery, warehouse, partner, picking_object)
                            if new_picking:
                                self.make_picking_ready(new_picking)
                
                except Exception as e:
                    log_object.log_error(title=_(f"Error during {delivery.get('order_number')} order synchronization."), message=_(e))

            log_object.log_info(title=_(f"Orders synchronization successfully completed."))

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
        #Vérifier le statut de la commande fournisseur
        #Si statut = reçu, vérifier si transfert interne est présent dans Odoo en se basant sur les lignes de commandes (a voir si on se base sur autre chose)
        #Si transfert interne est présent dans Odoo on vérifie son statut
        #Si non validé on le valide
        """Synchronize receptions with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']
        product_product_object = self.env['product.product']
        move_object = self.env['stock.move']
        move_line_object = self.env['stock.move.line']

        warehouse = self.api_connection_id.warehouse_id
        partner = self.api_connection_id.default_delivery_partner_id
        arrival_status = self.api_connection_id.crosslog_reception_state_ids

        try:
            log_object.log_info(title=_(f"Receptions synchronization started."))
            receptions = self.api_connection_id.process_get_supplier_orders_updated_request()
            arrival_codes = {str(c) for c in arrival_status.mapped('code') if c is not None}
            #Gérer les batchs
            for reception in receptions:
                try:
                    state = reception.get('state')
                    order_number = reception.get('order_number')
                    if not state:
                        log_object.log_warning(f"Reception state is missing in the response for {order_number} reception.")
                        continue
                    if not order_number:
                        log_object.log_warning(f"Reception order number is missing in the response.")
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
                        if picking:
                            lines = reception.get('order_lines') or []
                            if not lines:
                                log_object.log_warning(f"No order lines from Crosslog for {order_number} reception.")
                                continue
                            track_lot = False
                            for line in lines:
                                product = product_product_object.search([('default_code', '=', line['code'])], limit=1)
                                receipt_qty = float(line['receipt_qty'] or 0.0)
                                initial_qty = float(line['initial_qty'] or 0.0)
                                if not product:
                                    log_object.log_warning(f"No product {line['code']} found in Odoo for {order_number} reception.")
                                    continue
                                move = picking.move_ids.filtered(lambda m: m.product_id.id == product.id)
                                if move:
                                    move._action_confirm()
                                    move._do_unreserve()  # on part propre : pas de reliquats précédents
                                    move.write({'product_uom_qty': receipt_qty})
                                    move._action_assign()

                                    ml = move.move_line_ids[:1]  # la ligne de réservation
                                    if not ml:
                                        # fallback : s'il n'y a pas eu de ligne, on en crée une
                                        ml = move_line_object.create({
                                            'move_id': move.id,
                                            'product_id': move.product_id.id,
                                            'product_uom_id': move.product_uom.id,
                                            'picking_id': move.picking_id.id,
                                            'location_id': move.location_id.id,
                                            'location_dest_id': move.location_dest_id.id,
                                            'reserved_uom_qty': receipt_qty,  # réservé
                                        })

                                    # 3) Transformer la ligne réservée en "faite"
                                    ml.write({
                                        'qty_done': receipt_qty,
                                        'reserved_uom_qty': receipt_qty,   # garder aligné évite des reliquats bizarres
                                    })
                                else:
                                    move_vals = {
                                        'name': product.name,
                                        'product_id': product.id,
                                        'product_uom_qty': initial_qty,
                                        'reserved_availability': initial_qty,
                                        'quantity_done': receipt_qty,
                                        'picking_id': picking.id,
                                        'location_id': picking.location_id.id,
                                        'location_dest_id': picking.location_dest_id.id
                                    }
                                    if product.tracking == 'lot':
                                        track_lot = True
                                    move_object.create(move_vals)
                                    log_object.log_info(f"New line created on transfer {picking.name} with product {product.name}.")

                            self.make_picking_ready(picking)
                            if track_lot is False:
                                self.validate_picking(picking)

                            picking.crosslog_synchronized = True
                            picking.crosslog_code = order_number

                except Exception as e:
                    log_object.log_error(title=_(f"Error during {order_number} reception synchronization."), message=(e))

            log_object.log_info(title=_(f"Receptions synchronization successfully completed."))

        except Exception as e:
            log_object.log_error(title=_(f"Error during receptions synchronization."), message=(e))

    def make_picking_ready(self, picking):
        picking.action_confirm()
        picking.action_assign()
            
    def validate_picking(self, picking):
        picking._action_done()
    
    def synchronize_pickings(self):
        """Synchronize pickings with Crosslog."""
        self.ensure_one()
        if not self.sync_deliveries and not self.sync_receptions:
            raise UserError("Please select at least one synchronization option (deliveries or receptions).")

        if self.sync_deliveries:
            self.synchronize_deliveries()

        if self.sync_receptions:
            self.synchronize_receptions()