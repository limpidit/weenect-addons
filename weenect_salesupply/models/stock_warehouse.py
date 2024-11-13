
from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_salesupply = fields.Boolean(string="Salesupply", default=False)

    id_salesupply = fields.Integer(string="Salesupply id")
    name_salesupply = fields.Char(string="Salesupply name")
    shop_id = fields.Many2one(comodel_name='salesupply.shop', string="Shop")
    
    @api.model
    def default_get(self, fields_list):
        res = super(StockWarehouse, self).default_get(fields_list)
        if self.env.context.get('salesupply'):
            res['is_salesupply'] = True
        return res