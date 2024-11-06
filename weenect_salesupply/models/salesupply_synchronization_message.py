
from odoo import models, fields

TYPES = [
    ('info', 'Information'),
    ('error', 'Error'),
    ('warning', 'Warning'),
]


class SalesupplySynchronizationMessage(models.Model):
    _name = 'salesupply.synchronization.message'
    _description = 'Information messages about a synchronization action'
    _order = 'create_date desc'
    
    synchronization_id = fields.Many2one(comodel_name='salesupply.synchronization', string="Synchronization", ondelete='cascade', readonly=True)
    
    # Message
    title = fields.Char(string="Title", readonly=True)
    type = fields.Selection(selection=TYPES, string="Message type", default='info', readonly=True)
    logs = fields.Text(string="Information logs", readonly=True)
