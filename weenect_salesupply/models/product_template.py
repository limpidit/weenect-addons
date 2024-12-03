
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    salesupply_shop_product_ids = fields.One2many(comodel_name='salesupply.shop.product', inverse_name='product_tmpl_id', string="Salesupply products")
    available_on_salesupply = fields.Boolean(string="Available on Salesupply")
    
    @api.model
    def default_get(self, fields_list):
        res = super(ProductTemplate, self).default_get(fields_list)
        if self.env.context.get('salesupply'):
            res['available_on_salesupply'] = True
        return res
            
    def action_open_send_product_wizard(self):
        """Open window assistant to execute Odoo -> Salesupply products synchronization"""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Create products in Salesupply"),
            'res_model': 'salesupply.send.product.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'products_to_send': self.ids
            },
        }
        