
from odoo import models, fields, api

from datetime import datetime

STATES = [
    ('success', "Success"),
    ('error', "Error")
]


class SalesupplyLog(models.Model):
    _name = 'salesupply.log'
    _description = "History of data retrieving from Salesupply"

    name = fields.Char(string="name")
    state = fields.Selection(selection=STATES, string="State")
    execution_date = fields.Datetime(string="Synchronization execution date")
    message = fields.Text(string="Additional information")
    
    @api.model
    def log_message(self, title, message, state):
        self.create({
            'name': title,
            'state': state,
            'execution_date': datetime.now(),
            'message': message
        })

    @api.model
    def log_error(self, title, message=""):
        self.log_message(title, message, 'error')
        
    @api.model
    def log_success(self, title, message=""):
        self.log_message(title, message, 'success')
        