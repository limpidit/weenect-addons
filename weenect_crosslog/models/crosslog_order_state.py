
from odoo import models, fields


class CrosslogOrderState(models.Model):
    _name = 'crosslog.order.state'
    _description = "The state of orders in crosslog"

    name = fields.Char(string="Name", required=True)
    code = fields.Integer(string="Code", required=True)
