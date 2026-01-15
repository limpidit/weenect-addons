
from odoo import models, fields


class CrosslogReceptionState(models.Model):
    _name = 'crosslog.reception.state'
    _description = "The state of receptions in Crosslog"

    name = fields.Char(string="Name", required=True)
    code = fields.Integer(string="Code", required=True)
