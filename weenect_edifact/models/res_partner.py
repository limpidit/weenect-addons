
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    export_format = fields.Selection(selection=[('d96a', 'EDIFACT INVOIC D96A'), ('d01b', 'EDIFACT INVOIC D01B')], string="EDI invoice export format")