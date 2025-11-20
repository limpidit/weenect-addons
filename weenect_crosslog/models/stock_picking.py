
from odoo import models, fields, Command, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    crosslog_code = fields.Char(string="Crosslog code")
    crosslog_order_id = fields.Char(string="Crosslog order id")
    crosslog_synchronized = fields.Boolean(string="Synchronized with Crosslog", default=False, copy=False)
    is_transfered_to_crosslog = fields.Boolean(store=True)
    is_delivered_from_crosslog = fields.Boolean(store=True)
    is_returned_to_crosslog = fields.Boolean(store=True)

    def create_delivery(self, delivery, warehouse, partner):
        product_product_object = self.env['product.product']
        picking_object = self.env['stock.picking']
        lot_object = self.env['stock.lot']
        log_object = self.env['crosslog.log']

        move_line_vals = []
        error = False
        new_shipment = False
        crosslog_lines = delivery.get('order_lines', [])
        order_number = delivery.get('order_number')

        for line in crosslog_lines:
            crosslog_product_code = line.get('code')
            sent_qty = float(line.get('sent_qty') or 0.0)
            if sent_qty == 0:
                continue
            product = product_product_object.search([('default_code', '=', crosslog_product_code), ('available_on_crosslog', '=', True)], limit=1)
            if not product:
                log_object.log_warning(title=_(f"Order {order_number} not synchronised."), message= _(f"The product {crosslog_product_code} does not exist in Odoo or is not synchronised with Crosslog."))
                error = True
                break

            lots = line.get('lots')
            product_tracking_by_lot = product.tracking == 'lot'

            if lots and product_tracking_by_lot:
                for lot in lots:
                    lot_code = (lot.get('lot_code') or '').strip()
                    exist_lot = lot_object.search([('name', '=', lot_code), ('product_id', '=', product.id), ('available_on_crosslog', '=', True)], limit=1)
                    qty = float(lot.get('quantity') or 0.0)
                    if not exist_lot:
                        log_object.log_warning(title=_(f"Order {order_number} not synchronised."), message=_(f"The lot {lot_code} for the product {line['code']} does not exist in Odoo or is not synchronised with Crosslog."))
                        error = True
                        break
                    move_line_vals.append(Command.create({
                        'product_id': product.id,
                        'lot_id': exist_lot.id if exist_lot else False,
                        'qty_done': qty,
                    }))
            elif not lots and product_tracking_by_lot:
                log_object.log_warning(title=_(f"Order {order_number} not synchronised."), message=_(f"Product {crosslog_product_code} managed without lot in Crosslog while managed with lot in Odoo for order {order_number}."))
                error = True
                break
            elif lots and not product_tracking_by_lot:
                log_object.log_warning(title=_(f"Order {order_number} not synchronised."), message=_(f"Product {crosslog_product_code} managed with lot in Crosslog while managed without lot in Odoo for order {order_number}."))
                error = True
                break    
            else:
                move_line_vals.append(Command.create({
                    'product_id': product.id,
                    'qty_done': sent_qty,
                }))
            
            if error:
                break
        
        if not error:
            new_shipment = picking_object.create({
                'partner_id': partner.id,
                'picking_type_id': warehouse.out_type_id.id,
                'crosslog_synchronized': True,
                'crosslog_code': delivery.get('order_number'),
                'move_line_ids': move_line_vals,
            })
        return new_shipment


    def create_return(self, lines, return_number, order_number, delivery):
        product_product_object = self.env['product.product']
        log_object = self.env['crosslog.log']
        picking_object = self.env['stock.picking']
        move_object = self.env['stock.move']
        move_line_object = self.env['stock.move.line']

        return_picking = False
        for line in lines:
            receipt_qty = float(line['receipt_qty'] or 0.0)
            if receipt_qty > 0:
                product = product_product_object.search([('default_code', '=', line['code']), ('available_on_crosslog', '=', True)], limit=1)
                if not product:
                    log_object.log_warning(title=_(f"Return {return_number} not synchronized"), message=_(f"Product {line['code']} not found in Odoo or is not synchronized."))
                    return_picking = False
                    break

                move = delivery.move_ids.filtered(lambda m: m.product_id.id == product.id)
                if not move:
                    log_object.log_warning(title=_(f"Return {return_number} not synchronized"), message=_(f"No line on delivery {order_number} with product {line['code']} matched."))
                    return_picking = False
                    break
                
                if not return_picking:
                    return_type = delivery.picking_type_id.return_picking_type_id or delivery.picking_type_id
                    return_picking = picking_object.create({
                        'picking_type_id': return_type.id,
                        'company_id': delivery.company_id.id,
                        'origin': f"Return of {order_number}",
                        'partner_id': delivery.partner_id.id,
                        'location_id': delivery.location_dest_id.id,
                        'location_dest_id': delivery.location_id.id,
                    })

                ret_move = move_object.create({
                    'reference': move.reference or product.display_name,
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

                ml_vals = []

                if product.tracking in ('lot', 'serial'):
                    if receipt_qty == move.quantity:
                        orig_mls = move.move_line_ids.filtered(lambda l: l.qty_done > 0)
                        for orig_ml in orig_mls:
                            if orig_ml.lot_id:
                                ml_vals.append({
                                    'move_id': ret_move.id,
                                    'picking_id': return_picking.id,
                                    'product_id': product.id,
                                    'product_uom_id': move.product_uom.id,
                                    'qty_done': orig_ml.qty_done,
                                    'location_id': return_picking.location_id.id,
                                    'location_dest_id': return_picking.location_dest_id.id,
                                    'lot_id': orig_ml.lot_id.id,
                                })
                            else:
                                log_object.log_warning(title=_(f"Return {return_number} not synchronized"), message=_(f"Product {line['code']} requires lot/serial number but none found on original move line."))
                                return_picking = False
                                break
                    else:
                        orig_ml = move.move_line_ids.filtered(lambda l: l.qty_done > 0)[:1]
                        if orig_ml.lot_id:
                            ml_vals.append({
                                'move_id': ret_move.id,
                                'picking_id': return_picking.id,
                                'product_id': product.id,
                                'product_uom_id': move.product_uom.id,
                                'qty_done': receipt_qty,
                                'location_id': return_picking.location_id.id,
                                'location_dest_id': return_picking.location_dest_id.id,
                                'lot_id': orig_ml.lot_id.id,
                            })
                            ml_vals['lot_id'] = orig_ml.lot_id.id
                        else:
                            log_object.log_warning(title=_(f"Return {return_number} not synchronized"), message=_(f"Product {line['code']} requires lot/serial number but none found on original move line."))
                            return_picking = False
                            break

                move_line_object.create(ml_vals)
        return return_picking

    def make_picking_ready(self):
        self.action_confirm()
        self.action_assign()
            
    def validate_picking(self):
        self.button_validate()