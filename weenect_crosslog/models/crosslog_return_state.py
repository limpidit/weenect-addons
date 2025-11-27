
from odoo import models, fields


class CrosslogReturnState(models.Model):
    _name = 'crosslog.return.state'
    _description = "The state of returns in Crosslog"

    name = fields.Char(string="Name", required=True)
    code = fields.Integer(string="Code", required=True)
