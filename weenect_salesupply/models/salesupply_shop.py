
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from .salesupply_request import SalesupplyRequest

import traceback


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
    default_customer_id = fields.Many2one(comodel_name='res.partner', string="Default orders customer")
    last_orders_synchronization_date = fields.Datetime(string="Last synchronization")
    
    def get_products_from_salesupply(self, manual_execution=True):
        """
        Synchronizes products between Odoo and Salesupply.

        This method retrieves product data from Salesupply and links it to the corresponding 
        products in Odoo. If new products are found in Salesupply that are not yet linked in 
        Odoo, they are automatically linked. Logs are created to record the results of the 
        synchronization, including any errors or issues encountered during the process.

        Args:
            manual_execution (bool, optional): If True, the method returns an action that 
                opens a window displaying the synchronization logs. Defaults to True.

        Behavior:
        - Connects to Salesupply using the configured API credentials.
        - Retrieves product data for the associated Salesupply shop group.
        - For each product retrieved:
        - If the product exists in Odoo but is not yet linked to Salesupply, a link is created.
        - If an error occurs during synchronization of a specific product, it is logged.
        - Logs informational, warning, or error messages depending on the synchronization outcome.
        - Returns a window action displaying logs if `manual_execution` is True.

        Returns:
            dict or None: 
                - A dictionary containing an action to display the logs if executed manually.
                - None if executed by a planned action.

        Raises:
            Exception: If an unexpected error occurs while synchronizing a product.

        Dependencies:
            - SalesupplyRequest: A helper class to handle API requests to Salesupply.
            - Odoo models:
                - `product.template`: For managing Odoo products.
                - `salesupply.shop.product`: For linking Odoo products to Salesupply products.
                - `salesupply.log`: For recording logs of the synchronization process.
        """
        
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
    
    def action_open_inventory_wizard(self):
        """Open window assistant to execute inventory synchronization"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Make inventory"),
            'res_model': 'salesupply.inventory.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shop_id': self.id
            },
        }
    
    def get_deliveries_from_salesupply(self, manual_execution=True):
        return
        

            
    
    
        
        