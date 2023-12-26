from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_number = fields.Char(string='Numéro de Tracking')
    imei_filled = fields.Boolean(string='IMEI Renseignés')

