
from odoo import models, fields, api

from datetime import datetime, timedelta

TYPES = [
    ('info', "Information"),
    ('warning', "Warning"),
    ('error', "Error")
]


class SalesupplyLog(models.Model):
    _name = 'salesupply.log'
    _description = "History of data retrieving from Salesupply"
    _order = 'execution_date desc'

    name = fields.Char(string="name")
    type = fields.Selection(selection=TYPES, string="Type")
    execution_date = fields.Datetime(string="Synchronization execution date")
    message = fields.Text(string="Additional information")
    
    @api.model
    def log_message(self, title, message, type):
        new_log = self.create({
            'name': title,
            'type': type,
            'execution_date': datetime.now(),
            'message': message
        })
        return new_log

    @api.model
    def log_error(self, title, message=""):
        return self.log_message(title, message, 'error')
        
    @api.model
    def log_info(self, title, message=""):
        return self.log_message(title, message, 'info')
    
    @api.model
    def log_warning(self, title, message=""):
        return self.log_message(title, message, 'warning')
    
    @api.model
    def log_and_open_error(self, title, message=""):
        new_log = self.log_error(title, message)
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'view_mode': 'form',
            'res_model': 'salesupply.log',
            'res_id': new_log.id,
            'target': 'current',
        }
        
    def remove_older_logs(self):
        date_limit = datetime.today() - timedelta(days=30)
        logs_to_remove = self.search([('execution_date', '<', date_limit)])
        logs_to_remove.unlink() 