
from odoo import models, fields, _
import logging
_logger = logging.getLogger(__name__)

class CrosslogProductSynchronization(models.TransientModel):
    _name = 'crosslog.product.synchronization'
    _description = 'Crosslog Product Synchronization'

    api_connection_id = fields.Many2one(
        comodel_name='crosslog.connection',
        string='API Connection',
        required=True,
        help='Select the API connection to use for synchronization.',
    )

    synchronize_stock = fields.Boolean(
        string='Synchronize Stock',
        default=False,
        help='Check this box to synchronize stock levels with Crosslog.',
    )

    def synchronize_products(self, synchronize_stock=None):
        """Synchronize products with Crosslog."""
        self.ensure_one()
        product_object = self.env['product.product']
        quant_object = self.env['stock.quant']
        lot_object = self.env['stock.lot']
        log_object = self.env['crosslog.log']
        
        warehouse = self.api_connection_id.warehouse_id
        existing_quants = quant_object
        quant_vals = []
        
        if synchronize_stock is not None:
            self.synchronize_stock = synchronize_stock

        log_object.log_info(title=_(f"Products synchronization started."))

        for product in product_object.search([]):
            if self.api_connection_id.process_exist_item_request(product.default_code):
                product.available_on_crosslog = True
                if self.synchronize_stock:
                    product_information_result = self.api_connection_id.process_get_product_information_request(product.default_code)

                    if product.tracking == 'lot':
                        lots_data = product_information_result.get('lots') or []
                        if not lots_data:
                            log_object.log_warning(title=_(f"No lot retrieved for %s (%s), skipping.", product.display_name, product.default_code))
                        else:
                            for lot_info in lots_data:
                                lot_name = (lot_info.get('lot_number') or '').strip()
                                qty = float(lot_info.get('quantity') or 0.0)

                                if not lot_name:
                                    log_object.log_warning(title=_(f"Lot without name for %s, ignored.", product.default_code))
                                    continue

                                lot = lot_object.search([('name', '=', lot_name), ('product_id', '=', product.id)], limit=1)

                                if lot:
                                    lot.available_on_crosslog = True

                                    existing_quant = quant_object.search([('product_id', '=', product.id), ('location_id', '=', warehouse.lot_stock_id.id), ('lot_id', '=', lot.id)],  limit=1)
                                    if existing_quant:
                                        existing_quant.write({'inventory_quantity': qty})
                                        existing_quants |= existing_quant
                                    else:
                                        quant_vals.append({
                                            'product_id': product.id,
                                            'location_id': warehouse.lot_stock_id.id,
                                            'lot_id': lot.id,
                                            'inventory_quantity': qty,
                                        })

                                else:
                                    lot = lot_object.create({
                                        'name': lot_name,
                                        'product_id': product.id,
                                        'available_on_crosslog': True,
                                    })
                                    quant_vals.append({
                                        'product_id': product.id,
                                        'location_id': warehouse.lot_stock_id.id,
                                        'lot_id': lot.id,
                                        'inventory_quantity': qty,
                                    })
                    else:
                        existing_quant = quant_object.search([('product_id', '=', product.id), ('location_id', '=', warehouse.lot_stock_id.id)], limit=1)
                        if existing_quant:
                            existing_quant.write({'inventory_quantity': float(product_information_result['available_qty']) + float(product_information_result['reserved_qty'])})
                            existing_quants |= existing_quant
                        else:
                            quant_vals.append({
                                'product_id': product.id,
                                'location_id': warehouse.lot_stock_id.id,
                                'inventory_quantity': float(product_information_result['available_qty']) + float(product_information_result['reserved_qty']),
                            })
                        
            else:
                product.available_on_crosslog = False

        if quant_vals:
            new_quants = quant_object.create(quant_vals)
            existing_quants |= new_quants
        
        if existing_quants:
            for existing_quant in existing_quants:
                existing_quant.action_apply_inventory()

        log_object.log_info(title=_(f"Products synchronization completed."))
            
        return