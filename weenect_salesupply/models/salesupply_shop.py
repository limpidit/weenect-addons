
from odoo import models, fields
from odoo.exceptions import ValidationError
import logging

from .salesupply_request import SalesupplyRequest

_logger = logging.getLogger()


class SalesupplyShop(models.Model):
    _name = 'salesupply.shop'
    _description = 'Salesupply shop'
    
    name = fields.Char(string="Name")
    connection_id = fields.Many2one(comodel_name='salesupply.connection', string="Associated API config")
    id_salesupply = fields.Integer(string="ID Salesupply")
    shop_owner_id_salesupply = fields.Integer(string="ID shop owner")
    shop_group_id_salesupply = fields.Integer(string="ID shop group")
    active = fields.Boolean(string="Active")
        