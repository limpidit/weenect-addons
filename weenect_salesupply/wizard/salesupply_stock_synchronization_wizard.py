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

            for warehouse in warehouses:
                salesupply_receptions = salesupply._get_receptions(warehouse.shop_id.shop_owner_id_salesupply, warehouse.id_salesupply, self.date_from_synchronization)
                if 'error_message' in salesupply_receptions:
                    logs |= log_object.log_error(title=_("Error while retrieving receptions"), message=salesupply_receptions['error_message'])
                    continue
                logs |= log_object.log_info(title=_(f"Starting synchronization of {warehouse.name} receptions"), message=str(salesupply_receptions))
                    
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
                            logs |= assigned_reception._validate_internal_transfer_from_salesupply(reception_details_json)

                quants_to_remove = quant_object.search([('location_id', '=', warehouse.lot_stock_id.id)]).filtered(lambda q: not q.lot_id.is_default_salesupply_lot):
                quanitities_by_product = {}
                
                for quant in quants_to_remove:
                    quanitities_by_product[quant.product_id] = quanitities_by_product.get(quant.product_id, 0) + quant.quantity
                    quant.action_set_inventory_quantity_to_zero()
                    
                for product, quantity in quanitities_by_product.items():
                    quant_object._update_available_quantity(product, warehouse.lot_stock_id, quantity)
                    
                quant_object._unlink_zero_quants()
                
                                                    
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