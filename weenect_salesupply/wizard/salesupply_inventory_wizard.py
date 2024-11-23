
from odoo import models, fields, api, _

from ..models.salesupply_request import SalesupplyRequest


class SalesupplyInventoryWizard(models.TransientModel):
    _name = 'salesupply.inventory.wizard'
    _description = 'Assistant window to synchronize inventory between Salesupply and Odoo'

    warehouse_ids = fields.Many2many(comodel_name='stock.warehouse', string="Warehouses to synchronize", required=True,
        domain="[('is_salesupply', '=', True), ('shop_id', '=', shop_id)]")
    shop_id = fields.Many2one(comodel_name='salesupply.shop', string="Shop", required=True,
        default=lambda self: self.env.context.get('default_shop_id'))
    
    def synchronize_inventory(self):
        stock_quant_object = self.env['stock.quant']
        log_object = self.env['salesupply.log']
        salesupply = SalesupplyRequest(self.shop_id.connection_id)
        
        inventory_lines = stock_quant_object
        logs = log_object
                
        for warehouse in self.warehouse_ids:
            id_salesupply_warehouse = warehouse.id_salesupply
            location = warehouse.lot_stock_id
            
            response = salesupply._get_warehouse_stock(id_salesupply_warehouse)
            if 'error_message' in response:
                return log_object.log_and_open_error(
                    _("Error while synchronizing inventory"), 
                    response['error_message']
                )

            for item in response:
                product_id = item.get('ProductId')
                qty_on_hand = item.get('QtyOnHand')
                shop_product = self.env['salesupply.shop.product'].search([('id_salesupply', '=', product_id)], limit=1)
                if not shop_product:
                    logs = logs | log_object.log_info(_(f"Product {product_id} not existing in Odoo"))
                    continue
                product = shop_product.product_tmpl_id.product_variant_id
                inventory_line = stock_quant_object.search([('product_id', '=', product.id), ('location_id', '=', location.id)], limit=1)
                if inventory_line:
                    if inventory_line.inventory_quantity == qty_on_hand:
                        continue
                    logs = logs | log_object.log_info(
                        _(f"Updated quantity for {product.name_get()} : {inventory_line.inventory_quantity} -> {qty_on_hand}")
                    )
                    inventory_line.inventory_quantity = qty_on_hand
                else:
                    logs = logs | log_object.log_info(
                        _(f"Updated quantity for {product.name_get()} : 0 -> {qty_on_hand}")
                    )
                    inventory_line = stock_quant_object.create({
                        'product_id': product.id,
                        'location_id': location.id,
                        'inventory_quantity': qty_on_hand,
                    })
                inventory_lines = inventory_lines | inventory_line
                
        inventory_lines.action_apply_inventory()
        
        return {
            'type': 'ir.actions.act_window',
            'name': "Inventory synchronization logs",
            'view_mode': 'tree,form',
            'res_model': 'salesupply.log',
            'target': 'new',
            'id': self.env.ref('weenect_salesupply.salesupply_log_action').id,
            'context': {'create': False},
            'domain': [('id', 'in', logs.ids)]
        }
            