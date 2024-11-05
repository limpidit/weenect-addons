
from odoo import models, fields
from odoo.exceptions import ValidationError
import logging

from .salesupply_request import SalesupplyRequest

_logger = logging.getLogger()


class SalesupplyShop(models.Model):
    _name = 'salesupply.shop'
    _description = 'Salesupply shop'
    
    name = fields.Char(string="Name")
    id_salesupply = fields.Integer(string="ID Salesupply")
    shop_owner_id_salesupply = fields.Integer(string="ID shop owner")
    shop_group_id_salesupply = fields.Integer(string="ID shop group")
    active = fields.Boolean(string="Active")
    
    def synchronize_shops(self):
        company = self.env.company
        salesupply = SalesupplyRequest(company)
        shops_result = salesupply._get_shops()
        if 'error_message' in shops_result:
            raise ValidationError(shops_result['error_message'])
        for element in shops_result:
            existing_shop = self.search([('id_salesupply', '=', element['Id'])])
            if existing_shop:
                existing_shop.write({
                    'name': element['Name'],
                    'shop_owner_id_salesupply': element['ShopOwnerId'],
                    'shop_group_id_salesupply': element['ShopGroupId'],
                    'active': element['Active']
                })
            else:
                new_shop = self.create({
                    'id_salesupply': element['Id'],
                    'name': element['Name'],
                    'shop_owner_id_salesupply': element['ShopOwnerId'],
                    'shop_group_id_salesupply': element['ShopGroupId'],
                    'active': element['Active']
                })
                _logger.info(f"New shop created : {new_shop.name}")
            
        