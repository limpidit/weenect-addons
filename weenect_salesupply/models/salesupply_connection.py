
from odoo import models, fields, _
from odoo.exceptions import UserError
import logging

from .salesupply_request import SalesupplyRequest

_logger = logging.getLogger()

ENVIRONMENTS = [('test', "Testing environment"), ('prod', "Production environment")]


class SalesupplyConnection(models.Model):
    _name = 'salesupply.connection'
    _description = "Salesupply API configuration"
    
    name = fields.Char(string="Name")
    
    # API Connection
    api_host = fields.Char(string="API url")
    api_username = fields.Char(string="API username")
    api_password = fields.Char(string="API password")

    environment = fields.Selection(selection=ENVIRONMENTS, string="Environment")
    active = fields.Boolean(string="Active ?", default=False)
    
    def display_enabling_connection_message(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Warning"),
                'message': _("You have to enable this connection first !"),
                'type': 'warning',
                'sticky': False,
            }
        }
    
    def connection_test(self):
        self.ensure_one()
        if not self.active:
            return self.display_enabling_connection_message()
        salesupply = SalesupplyRequest(self)
        connection_test = salesupply._get_api_user_info()
        if isinstance(connection_test, dict) and 'error_message' in connection_test:
            raise UserError(_(f"Connection test failed : {connection_test['error_message']}"))
        message = _("Connection Test Successful!")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        } 
    
    def synchronize_shops(self):
        self.ensure_one()
        if not self.active:
            return self.display_enabling_connection_message()
        shop_object = self.env['salesupply.shop']
        salesupply = SalesupplyRequest(self)
        shops_result = salesupply._get_shops()
        if 'error_message' in shops_result:
            raise UserError(_(f"Synchronization failed : {shops_result['error_message']}"))
        for element in shops_result:
            existing_shop = shop_object.search([('id_salesupply', '=', element['Id'])])
            if existing_shop:
                existing_shop.write({
                    'name': element['Name'],
                    'connection_id': self.id,
                    'shop_owner_id_salesupply': element['ShopOwnerId'],
                    'shop_group_id_salesupply': element['ShopGroupId'],
                    'active': element['Active']
                })
            else:
                new_shop = shop_object.create({
                    'id_salesupply': element['Id'],
                    'name': element['Name'],
                    'shop_owner_id_salesupply': element['ShopOwnerId'],
                    'shop_group_id_salesupply': element['ShopGroupId'],
                    'active': element['Active']
                })
                _logger.info(f"SALESUPPLY : New shop created -> {new_shop.name}")
        return {
            'type': 'ir.actions.act_window',
            'name': "Shops",
            'view_mode': 'tree',
            'res_model': 'salesupply.shop',
            'target': 'current',
        }

    