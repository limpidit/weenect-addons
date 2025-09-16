
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sender_gln_id = fields.Many2one(comodel_name='res.partner.id_number', string="GLN expéditeur", config_parameter='weenect_edifact.sender_gln')
    sagaflor_gln_id = fields.Many2one(comodel_name='res.partner.id_number', string="GLN Sagaflor", config_parameter='weenect_edifact.sagaflor_gln')
    futterhaus_gln_id = fields.Many2one(comodel_name='res.partner.id_number', string="GLN Futterhaus", config_parameter='weenect_edifact.futterhaus_gln')
