from odoo import models, fields, api
import base64
from io import StringIO
from datetime import datetime

class ResPartner(models.Model):
    _inherit = 'res.partner'

    gln=fields.Char(string="GLN")
