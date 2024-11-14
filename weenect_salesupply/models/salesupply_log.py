
from odoo import models, fields, api

from datetime import datetime, timedelta

STATES = [
    ('success', "Success"),
    ('error', "Error")
]


class SalesupplyLog(models.Model):
    _name = 'salesupply.log'
    _description = "History of data retrieving from Salesupply"
    _order = 'execution_date desc'

    name = fields.Char(string="name")
    state = fields.Selection(selection=STATES, string="State")
    execution_date = fields.Datetime(string="Synchronization execution date")
    message = fields.Text(string="Additional information")
    
    @api.model
    def log_message(self, title, message, state):
        new_log = self.create({
            'name': title,
            'state': state,
            'execution_date': datetime.now(),
            'message': message
        })
        return new_log

    @api.model
    def log_error(self, title, message=""):
        return self.log_message(title, message, 'error')
        
    @api.model
    def log_success(self, title, message=""):
        return self.log_message(title, message, 'success')
        
    def remove_older_logs(self):
        date_limit = datetime.today() - timedelta(days=30)
        logs_to_remove = self.search([('execution_date', '<', date_limit)])
        logs_to_remove.unlink()