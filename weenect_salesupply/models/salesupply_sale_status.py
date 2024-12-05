
from odoo import models, fields


class SalesupplySaleStatus(models.Model):
    _name = 'salesupply.sale.status'
    _description = "Define sale orders statuses on Salesupply"

    name = fields.Char(string="Name")

    id_salesupply = fields.Integer(string="Salesupply Id")
    id_base_status = fields.Integer(string="Salesupply base status Id")
    id_type_status = fields.Integer(string="Salesupply type status Id")
