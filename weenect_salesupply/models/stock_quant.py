
from odoo import models, fields, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    # Add your custom fields or methods here
    custom_field = fields.Char(string='Custom Field')

    def _update_salesupply_quants(self, warehouse, default_lot_name):
        lot_object = self.env['stock.lot']
        
        quants_to_remove = self.search([('location_id', '=', warehouse.lot_stock_id.id), ('lot_id.is_default_salesupply_lot', '=', False)])
        quantities_by_product = {}
        
        for quant in quants_to_remove:
            quantities_by_product[quant.product_id] = quantities_by_product.get(quant.product_id, 0) + quant.quantity

        quants_to_remove.inventory_quantity = 0
        quants_to_remove.action_apply_inventory()
            
        default_lots = lot_object.search([('product_id', 'in', quantities_by_product.keys()), ('is_default_salesupply_lot', '=', True)])
        default_lot_map = {lot.product_id: lot for lot in default_lots}

        for product, quantity in quantities_by_product.items():
            lot_id = default_lot_map.get(product)
            if not lot_id:
                lot_id = lot_object.create({'name': default_lot_name, 'product_id': product.id, 'is_default_salesupply_lot': True})
                default_lot_map[product] = lot_id
            self._update_available_quantity(product, warehouse.lot_stock_id, quantity, lot_id=lot_id)
            
        self._unlink_zero_quants()
        