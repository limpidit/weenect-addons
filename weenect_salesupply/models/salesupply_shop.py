
from odoo import models, fields, _
from odoo.exceptions import ValidationError

from .salesupply_request import SalesupplyRequest


class SalesupplyShop(models.Model):
    _name = 'salesupply.shop'
    _description = 'Salesupply shop'
    
    name = fields.Char(string="Name")
    connection_id = fields.Many2one(comodel_name='salesupply.connection', string="Associated API config")
    id_salesupply = fields.Integer(string="ID Salesupply")
    shop_owner_id_salesupply = fields.Integer(string="ID shop owner")
    shop_group_id_salesupply = fields.Integer(string="ID shop group")
    active = fields.Boolean(string="Active")
    
    # Shippings synchronization
    sale_done_status_ids = fields.Many2many(comodel_name='salesupply.sale.status', string="Delivered picking states")
    
    def get_products_from_salesupply(self, manual_execution=True):
        product_object = self.env['product.template']
        salesupply_shop_product_object = self.env['salesupply.shop.product']
        log_object = self.env['salesupply.log']
        
        shop_group = self.shop_group_id_salesupply
        logs = log_object
        salesupply = SalesupplyRequest(self.connection_id)
        response = salesupply._get_shop_group_products(shop_group)
        
        if 'error_message' in response:
            return log_object.log_and_open_error(
                _("Error while retrieving products"), 
                response['error_message']
            )
            
        for product in response:
            try:
                if not product['Code']:
                    continue
                id_product = product['Id']
                existing_product = product_object.search([('default_code', '=', product['Code'])])
                if not existing_product:
                    continue
                if id_product not in existing_product.salesupply_shop_product_ids.mapped('id_salesupply'):
                    salesupply_shop_product_object.create({
                        'product_tmpl_id': existing_product.id,
                        'id_salesupply': id_product,
                        'id_shop_group': shop_group
                    })
                    logs = logs | log_object.log_info(_(f"Product synchronized -> {existing_product.name}"))
                existing_product.available_on_salesupply = True
            except Exception as exception:
                logs = logs | log_object.log_error(_(f"Could not synchronize a product"), str(exception))
        
        if len(logs) == 0:
            logs = logs | log_object.log_info(_("No new link between Odoo and Salesupply products."))
        elif logs.filtered(lambda r: r.type == 'error'):
            logs = logs | log_object.log_warning(_("Product synchronization done with failures"))
        else:
            logs = logs | log_object.log_info(_("Products retrieved successfully from Salesupply"))

        if manual_execution:
            return {
                'type': 'ir.actions.act_window',
                'name': "Linking Salesupply and Odoo products logs",
                'view_mode': 'tree,form',
                'res_model': 'salesupply.log',
                'target': 'new',
                'id': self.env.ref('weenect_salesupply.salesupply_log_action').id,
                'context': {'create': False},
                'domain': [('id', 'in', logs.ids)]
            }
        
        return
                
                
        