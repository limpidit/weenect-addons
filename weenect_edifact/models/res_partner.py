
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    edi_export_format = fields.Selection(selection=[('d96a', 'Sagaflor'), ('d01b', 'Futterhaus')], string="EDI invoice export format")