from odoo import api, models, fields, tools

class IrAttachment(models.Model):

    _inherit = "ir.attachment"

    is_sda = fields.Boolean(string='Est une SDA')
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    is_sda_reference=fields.Boolean(string='Est la SDA de référence')
    is_sda_definitive=fields.Boolean(string='Est la SDA définitive')
