
from odoo import models, fields, _


class StockQuant(models.Model):
    """
    Inherits stock.quant model to add custom methods for updating and synchronizing inventory with Salesupply.
    Methods
    -----------------------------------------------------------------------------------------------------
        _update_salesupply_quants(warehouse, default_lot_name)
            Updates the quantities of quants in the specified warehouse and assigns them to default Salesupply lots.
        _make_inventory_from_salesupply(salesupply, warehouse)
            Synchronizes the inventory in Odoo with the stock levels from Salesupply for the specified warehouse.
    """
    _inherit = 'stock.quant'

    def _update_salesupply_quants(self, warehouse, default_lot_name):
        lot_object = self.env['stock.lot']
        
        quants_to_remove = self.search([('location_id', '=', warehouse.lot_stock_id.id), ('lot_id.is_default_salesupply_lot', '=', False)])
        quantities_by_product = {}
        
        for quant in quants_to_remove:
            quantities_by_product[quant.product_id.id] = quantities_by_product.get(quant.product_id.id, 0) + quant.quantity

        quants_to_remove.inventory_quantity = 0
        quants_to_remove.action_apply_inventory()
            
        default_lots = lot_object.search([('product_id', 'in', list(quantities_by_product.keys())), ('is_default_salesupply_lot', '=', True)])
        default_lot_map = {lot.product_id.id: lot for lot in default_lots}

        for product, quantity in quantities_by_product.items():
            lot_id = default_lot_map.get(product)
            if not lot_id:
                lot_id = lot_object.create({'name': default_lot_name, 'product_id': product, 'is_default_salesupply_lot': True})
                default_lot_map[product] = lot_id
            self._update_available_quantity(lot_id.product_id, warehouse.lot_stock_id, quantity, lot_id=lot_id)
            
        self._unlink_zero_quants()
        
    def _make_inventory_from_salesupply(self, salesupply, warehouse):
        log_object = self.env['salesupply.log']
        
        id_salesupply_warehouse = warehouse.id_salesupply
        location = warehouse.lot_stock_id
        
        response = salesupply._get_warehouse_stock(id_salesupply_warehouse)
        if 'error_message' in response:
            log_object.log_error(_("Error while synchronizing inventory"), response['error_message'])
            return

        for item in response:
            product_id = item.get('ProductId')
            qty_on_hand = item.get('QtyOnHand')
            shop_product = self.env['salesupply.shop.product'].search([('id_salesupply', '=', product_id)], limit=1)
            if not shop_product:
                log_object.log_warning(_(f"Product {product_id} not existing in Odoo"))
                continue
            product = shop_product.product_tmpl_id.product_variant_id
            inventory_line = self.search([('product_id', '=', product.id), ('location_id', '=', location.id)], limit=1)
            if inventory_line:
                if inventory_line.inventory_quantity == qty_on_hand:
                    continue
                log_object.log_info(_(f"Updated quantity for {product.display_name} : {inventory_line.inventory_quantity} -> {qty_on_hand}"))
                inventory_line.inventory_quantity = qty_on_hand
            else:
                log_object.log_info(_(f"Updated quantity for {product.display_name} : 0 -> {qty_on_hand}"))
                inventory_line = self.create({
                    'product_id': product.id,
                    'location_id': location.id,
                    'inventory_quantity': qty_on_hand,
                })
            self |= inventory_line
                
        self.action_apply_inventory()
        return
        