
from odoo import models, fields, _
from odoo.exceptions import UserError

import json

from ..models.salesupply_request import SalesupplyRequest


class SalesupplySendProductWizard(models.TransientModel):
    _name = 'salesupply.send.product.wizard'
    _description = "Send products to specific Salesupply shops"

    shop_ids = fields.Many2many(comodel_name='salesupply.shop', string="Shops to send products on", required=True)
    product_tmpl_ids = fields.Many2many(comodel_name='product.template', string="Products to synchronize",
        default=lambda self: self.env.context.get('products_to_send'))

    def send_products_to_salesupply(self):
        self.ensure_one()
        log_object = self.env['salesupply.log']
        shop_product_object = self.env['salesupply.shop.product']
        shop_product_vals = []
        logs = log_object
        
        for shop in self.shop_ids:
            salesupply = SalesupplyRequest(shop.connection_id)
            shop_group = shop.shop_group_id_salesupply
            
            for product in self.product_tmpl_ids:
                if product.salesupply_shop_product_ids.filtered(lambda r: r.id_shop_group == shop_group):
                    logs = logs | log_object.log_info(title=_(f"Product {product.name} already available on {shop.name}"))
                    continue
                
                product_data = {
                    'Name': product.name,
                    'Code': product.default_code,
                    'ShopGroupId': shop_group,
                    'Published': True,
                    'KeepStock': True,
                    'IsShippable': True
                }
                
                if product.ean_weenect:
                    product_data['EAN'] = product.ean_weenect
                    
                if product.weight:
                    product_data['Weight'] = product.weight
                    product_data['WeightUOMId'] = 200
                    
                if product.list_price:
                    product_data['PriceExVat'] = product.list_price

                try:
                    product_json = json.dumps(product_data, indent=4)
                    logs = logs | log_object.log_info(title=_(f"Preparing to send {product.name} to {shop.name}"), message=product_json)
                    response = salesupply._post_product(product_json)
                    logs = logs | log_object.log_info(title=_(f"Successfully synchronized {product.name} to {shop.name}"), message=response)
                    product.available_on_salesupply = True
                    shop_product_vals.append({
                        'product_tmpl_id': product.id,
                        'id_shop_group': shop_group,
                        'id_salesupply': response.get('Id'),
                    })
                    
                except Exception as exception:
                    logs = logs | log_object.log_error(title="Error while sending product", message=str(exception))
                    continue
        
        # Linking products in batch to optimize performances
        shop_product_object.create(shop_product_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': "Sending products to Salesupply logs",
            'view_mode': 'tree,form',
            'res_model': 'salesupply.log',
            'target': 'new',
            'id': self.env.ref('weenect_salesupply.salesupply_log_action').id,
            'context': {'create': False},
            'domain': [('id', 'in', logs.ids)]
        }
            
            