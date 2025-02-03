from odoo import fields, models, _

from ..models.salesupply_request import SalesupplyRequest


class SalesupplyStockSynchronizationWizard(models.TransientModel):
    _name = 'salesupply.stock.synchronization.wizard'
    _description = 'Salesupply Stock Synchronization Wizard'

    shop_ids = fields.Many2many(comodel_name='salesupply.shop', string="Shops")
    date_from_synchronization = fields.Date(string="Date from wich stock should be synchronized")

    def synchronize_stock(self, manual_execution=True):
        self.ensure_one()
        warehouse_object = self.env['stock.warehouse']
        picking_object = self.env['stock.picking']
        log_object = self.env['salesupply.log']
        quant_object = self.env['stock.quant']
        logs = log_object
        
        for shop in self.shop_ids:
            salesupply = SalesupplyRequest(shop.connection_id)
            
            warehouses = warehouse_object.search([('is_salesupply', '=', True), ('shop_id', '=', shop.id)])
            salesupply_returns = salesupply._get_returns(shop.id_salesupply, warehouses, self.date_from_synchronization)
            salesupply_shipments = salesupply._get_shipments(shop.id_salesupply, warehouses, self.date_from_synchronization)

            for warehouse in warehouses:
                log_object.log_info(title=_(f"Starting stock synchronization for warehouse {warehouse.name}"))
                
                # RECEPTIONS / INTERNAL TRANSFERS JL -> NL
                self._synchronize_receptions(salesupply, warehouse)
                self.env.cr.commit()
                
                # Updating lots to get the default Salesupply lot on new quants
                quant_object._update_salesupply_quants(warehouse, shop.default_lot_name)
                            
                # RETURNS Customers -> NL
                picking_object._return_pickings_from_salesupply(salesupply_returns[warehouse.id_salesupply])
                            
                # TODO : DELIVERIES
                picking_object._create_shipments_from_salesupply(salesupply_shipments[warehouse.id_salesupply])
                
                
                # TODO : Inventory adjustments
                
                                                    
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
            
    def _synchronize_receptions(self, salesupply, warehouse):
        log_object = self.env['salesupply.log']
        picking_object = self.env['stock.picking']

        salesupply_receptions = salesupply._get_receptions(warehouse.shop_id.shop_owner_id_salesupply, warehouse.id_salesupply, self.date_from_synchronization)
        if 'error_message' in salesupply_receptions:
            log_object.log_error(title=_("Error while retrieving receptions"), message=salesupply_receptions['error_message'])
        log_object.log_info(title=_(f"Starting synchronization of {warehouse.name} receptions"), message=str(salesupply_receptions))
            
        for salesupply_json_reception in salesupply_receptions:
            if isinstance(salesupply_json_reception, dict):
                assigned_reception = picking_object.search([
                    ('location_dest_id', '=', warehouse.lot_stock_id.id), 
                    ('state', '=', 'assigned'),
                    ('name', '=', salesupply_json_reception['OrderCode']),
                    ('salesupply_synchronized', '=', False)
                ])
                if assigned_reception:
                    reception_details_json = salesupply._get_reception_details(salesupply_json_reception['Id'])
                    assigned_reception._validate_internal_transfer_from_salesupply(reception_details_json)