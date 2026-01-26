
from odoo import models, fields, _
from odoo.exceptions import UserError


class CrosslogPickingSynchronization(models.TransientModel):
    _name = 'crosslog.picking.synchronization'
    _description = 'Crosslog Picking Synchronization'

    api_connection_id = fields.Many2one(
        comodel_name='crosslog.connection',
        string='API Connection',
        required=True,
        help='Select the API connection to use for synchronization.',
    )

    sync_deliveries = fields.Boolean(string="Synchronize deliveries")
    sync_receptions = fields.Boolean(string="Synchronize receptions")
    sync_returns = fields.Boolean(string="Synchronize returns")

    def synchronize_pickings(self):
        self.ensure_one()

        if not self.sync_deliveries and not self.sync_receptions and not self.sync_returns:
            raise UserError(_("Please select at least one option."))

        self.api_connection_id.synchronize_pickings(
            sync_deliveries=self.sync_deliveries,
            sync_receptions=self.sync_receptions,
            sync_returns=self.sync_returns,
        )