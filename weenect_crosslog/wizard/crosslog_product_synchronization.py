
from odoo import models, fields


class CrosslogProductSynchronization(models.TransientModel):
    _name = 'crosslog.product.synchronization'
    _description = 'Crosslog Product Synchronization'

    api_connection_id = fields.Many2one(
        comodel_name='crosslog.connection',
        string='API Connection',
        required=True,
        help='Select the API connection to use for synchronization.',
    )

    synchronize_stock = fields.Boolean(
        string='Synchronize Stock',
        default=False,
        help='Check this box to synchronize stock levels with Crosslog.',
    )

    def synchronize_products(self):
        """Synchronize products with Crosslog."""
        self.ensure_one()
        product_object = self.env['product.template']

        for product in product_object.search([]):
            if self.api_connection_id.process_exist_item_request(product.default_code):
                product.available_on_crosslog = True
                if self.synchronize_stock:
                    product_information_result = self.api_connection_id.process_get_product_information_request(product.default_code)
                    # TODO process the result
                    pass
            else:
                product.available_on_crosslog = False
        return