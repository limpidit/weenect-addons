
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
    
    def retrieve_products(self, manual_execution=True):
        product_object = self.env['product.template']
        salesupply_shop_product_object = self.env['salesupply.shop.product']
        log_object = self.env['salesupply.log']
        
        salesupply = SalesupplyRequest(self.connection_id)
        shop_groups = self.mapped(lambda r: r.shop_group_id_salesupply)
        message = []
        
        for shop_group in shop_groups:
            response = salesupply._get_shop_group_products(shop_group)
            if 'error_message' in response:
                new_log = log_object.log_error(
                    _("Error while retrieving products"), 
                    response['error_message']
                )
                return {
                    'type': 'ir.actions.act_window',
                    'name': "Log message",
                    'view_mode': 'form',
                    'res_model': 'salesupply.log',
                    'res_id': new_log.id,
                    'target': 'current',
                }
                
            for product in response:
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
                    message.append(_(f"Product synchronized -> {existing_product.name}")) 
                existing_product.available_on_salesupply = True
        
        if len(message) == 0:
            message.append(_("No new link between Odoo and Salesupply products."))
        end_log = log_object.log_success(_("Products retrieved successfully from Salesupply"), "\n".join(message))

        if manual_execution:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'salesupply.log',
                'id': self.env.ref('weenect_salesupply.salesupply_log_action').id,
                'res_id': end_log.id,
                'target': 'current',
            }
        
        return
                
                
        