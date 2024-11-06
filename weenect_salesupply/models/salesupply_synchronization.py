
from datetime import datetime, timedelta
import logging

from odoo import models, fields, _

_logger = logging.getLogger()

SYNCHRONIZED_DATA = [
    ('product', 'Product')
]
STATES = [
    ('new', 'New'),
    ('processing', 'Processing'),
    ('failed', 'Failed'),
    ('done', 'Done')
]


class SalesupplySynchronization(models.Model):
    _name = 'salesupply.synchronization'
    _description = "Salesupply synchronization"
    _order = 'create_date'
    
    def _get_synchronization_name(self):
        return _(f"Synchronization of {self.synchronizated_data} -> {self.name_updated_record}")
        
    name = fields.Char(string="Name", default='_get_synchronization_name')
    connection_id = fields.Many2one(comodel_name='salesupply.connection', string="Associated API config")
    synchronizated_data = fields.Selection(selection=SYNCHRONIZED_DATA, string="Synchronized data")
    state = fields.Selection(selection=STATES, string="State", default='new')
    synchronization_done_date = fields.Date(string="Date of synchronization")
    
    # Updated record
    id_updated_record = fields.Integer(string="Updated record id", required=True)
    name_updated_record = fields.Char(string="Updated record name", required=True)
    
    # History of the synchronization instance
    message_ids = fields.One2many(comodel_name='salesupply.synchronization.message', inverse_name='synchronization_id', string="Logs")
    
    def log_message(self, title, logs="", type='info'):
        self.ensure_one()
        self.env['salesupply.synchronization.message'].create({
            'synchronization_id': self.id,
            'title': title,
            'logs': logs,
            'type': type
        })
    
    def put_state_to_new(self):
        for record in self:
            if record.state != 'failed':
                raise UserWarning(_("This synchronization action is not failed."))
            record.state = 'new'
            self.log_message(_("The state of this action was changed manually to 'New'"))
            
            
    # Synchronization with Salesupply
    
    def execute(self):
        return
    
    def execute_batch(self):
        to_execute_synchronizations = self.search([('state', '=', 'new')], order='create_date asc', limit=100)
        for synchronization in to_execute_synchronizations:
            synchronization.execute()
            
    # Cleaning data
    def remove_finished_syncrhonizations(self):
        _logger.info("SALESUPPLY : Removing old finished synchronizations")
        date_limit = datetime.today() - timedelta(days=30)
        actions_to_remove = self.search([('state', '=', 'done'), ('synchronization_done_date', '<', date_limit)])
        actions_to_remove.unlink()
