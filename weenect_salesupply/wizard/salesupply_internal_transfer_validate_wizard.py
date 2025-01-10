
from odoo import models, fields, _

from ..models.salesupply_request import SalesupplyRequest


class SalesupplyInternalTransferValidateWizard(models.TransientModel):
    _name = 'salesupply.internal.transfer.validate.wizard'
    _description = "Synchronization of receptions from Salesupply to Odoo"

    shop_id = fields.Many2one(comodel_name='salesupply.shop', string="Shop", required=True,
        default=lambda self: self.env.context.get('default_shop_id'))
    warehouse_ids = fields.Many2many(comodel_name='stock.warehouse', relation='reception_wiz_warehouse_rel',
        string="Warehouses to synchronize", required=True, domain="[('is_salesupply', '=', True), ('shop_id', '=', shop_id)]")
    date_from_synchronization = fields.Date(string="Date from wich pickings should be synchronized")

    def synchronize_receptions(self, manual_execution=True):
        picking_object = self.env['stock.picking']
        log_object = self.env['salesupply.log']
        logs = log_object
        
        salesupply = SalesupplyRequest(self.shop_id.connection_id)

        for warehouse in self.warehouse_ids:
            salesupply_receptions = salesupply._get_receptions(warehouse.shop_id.shop_owner_id_salesupply, warehouse.id_salesupply, self.date_from_synchronization)
            if 'error_message' in salesupply_receptions:
                logs |= log_object.log_error(title=_("Error while retrieving receptions"), message=salesupply_receptions['error_message'])
                continue
            logs |= log_object.log_info(title=_(f"Starting synchronization of {warehouse.name} receptions"), message=salesupply_receptions)
                
            for salesupply_json_reception in salesupply_receptions:
                assigned_reception = picking_object.search([
                    ('location_dest_id', '=', warehouse.lot_stock_id.id), 
                    ('state', '=', 'assigned'),
                    ('name', '=', salesupply_json_reception['OrderCode']),
                    ('salesupply_synchronized', '=', False)
                ])
                if assigned_reception:
                    reception_details_json = salesupply._get_reception_details(salesupply_json_reception['Id'])
                    logs |= assigned_reception._validate_internal_transfer_from_salesupply(reception_details_json)
        
        if manual_execution:            
            return {
                'type': 'ir.actions.act_window',
                'name': "Synchronization of receptions",
                'view_mode': 'tree,form',
                'res_model': 'salesupply.log',
                'target': 'new',
                'id': self.env.ref('weenect_salesupply.salesupply_log_action').id,
                'context': {'create': False},
                'domain': [('id', 'in', logs.ids)]
            }