
from odoo import models, fields, _
import logging
_logger = logging.getLogger(__name__)


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

    def synchronize_products(self, synchronize_stock=None):
        self.ensure_one()
        self.api_connection_id.synchronize_products(
            synchronize_stock=self.synchronize_stock if synchronize_stock is None else synchronize_stock
        )