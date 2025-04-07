
from odoo import models, fields


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

    def synchronize_products(self):
        """Synchronize products with Crosslog."""
        self.ensure_one()
        product_object = self.env['product.product']
        quant_object = self.env['stock.quant']
        
        warehouse = self.api_connection_id.warehouse_id
        existing_quants = quant_object
        quant_vals = []

        for product in product_object:
            if self.api_connection_id.process_exist_item_request(product.default_code):
                product.available_on_crosslog = True
                # TODO : Gérer le cas des produits suivi par lot
                if self.synchronize_stock and product.tracking != 'lot':
                    product_information_result = self.api_connection_id.process_get_product_information_request(product.default_code)
                    existing_quant = quant_object.search([('product_id', '=', product.id), ('location_id', '=', warehouse.lot_stock_id.id)], limit=1)
                    if existing_quant:
                        existing_quant.write({'inventory_quantity': product_information_result['available_qty'] + product_information_result['reserved_qty']})
                        existing_quants |= existing_quant
                    else:
                        quant_vals.append({
                            'product_id': product.id,
                            'location_id': warehouse.lot_stock_id.id,
                            'inventory_quantity': product_information_result['available_qty'] + product_information_result['reserved_qty'],
                        })
            else:
                product.available_on_crosslog = False

        if quant_vals:
            new_quants = quant_object.create(quant_vals)
            existing_quants |= new_quants
        
        if existing_quants:
            existing_quants.action_apply_inventory()
            
        return