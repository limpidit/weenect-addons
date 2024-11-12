
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    futterhaus_edifact_invoiced_partner_id = fields.Many2one(comodel_name='res.partner', string="Futterhaus invoiced partner")
    sagaflor_edifact_invoiced_partner_id = fields.Many2one(comodel_name='res.partner', string="Sagaflor invoiced partner")