
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
        salesupply = SalesupplyRequest(self.shop_id.connection_id)
        
        inventory_lines = stock_quant_object
        
        for warehouse in self.warehouse_ids:
            id_salesupply_warehouse = warehouse.id_salesupply
            response = salesupply._get_warehouse_stock(id_salesupply_warehouse)
            location = warehouse.lot_stock_id

            for item in response:
                product_id = item.get('ProductId')
                qty_on_hand = item.get('QtyOnHand')
                shop_product = self.env['salesupply.shop.product'].search([('id_salesupply', '=', product_id)], limit=1)
                if not shop_product:
                    continue
                product = shop_product.product_tmpl_id.product_variant_id
                inventory_line = stock_quant_object.search([('product_id', '=', product.id), ('location_id', '=', location.id)], limit=1)
                if inventory_line:
                    inventory_line.inventory_quantity = qty_on_hand
                else:
                    inventory_line = stock_quant_object.create({
                        'product_id': product.id,
                        'location_id': location.id,
                        'inventory_quantity': qty_on_hand,
                    })
                inventory_lines = inventory_lines | inventory_line
                
        inventory_lines.action_apply_inventory()
                