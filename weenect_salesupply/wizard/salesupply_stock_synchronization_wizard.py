
from odoo import fields, models, _

from ..models.salesupply_request import SalesupplyRequest

from datetime import datetime


class SalesupplyStockSynchronizationWizard(models.TransientModel):
    """
    A wizard for synchronizing stock between Odoo and Salesupply.
    
    Attributes:
        shop_ids (Many2many): The shops to synchronize.
        date_from_synchronization (Date): The date from which stock should be synchronized.
        
    Methods:
        synchronize_stock(manual_execution=True):
            Synchronizes stock for the selected shops from Salesupply.
            Args:
                manual_execution (bool): Indicates if the synchronization is manually triggered.
            Returns:
                dict: An action to open the synchronization log if manually executed.
        _synchronize_receptions(salesupply, warehouse):
            Synchronizes receptions for a given warehouse from Salesupply.
            Args:
                salesupply (SalesupplyRequest): The Salesupply request object.
                warehouse (stock.warehouse): The warehouse to synchronize receptions for.
    """
    _name = 'salesupply.stock.synchronization.wizard'
    _description = 'Salesupply Stock Synchronization Wizard'

    shop_ids = fields.Many2many(comodel_name='salesupply.shop', string="Shops")
    date_from_synchronization = fields.Date(string="Date from wich stock should be synchronized")
    
    sync_deliveries = fields.Boolean(string="Synchronize deliveries")
    sync_receptions = fields.Boolean(string="Synchronize receptions")
    sync_returns = fields.Boolean(string="Synchronize returns")
    do_inventory = fields.Boolean(string="Do inventory")

    def synchronize_stock(self):
        """
        Synchronizes stock data between the local Odoo system and the Salesupply platform for the selected shops.
        This method performs the following steps for each shop:
        1. Initializes a SalesupplyRequest object for the shop.
        2. Retrieves the warehouses associated with the shop that are marked for Salesupply synchronization.
        3. Fetches return and shipment data from Salesupply for the specified warehouses and synchronization date.
        4. Logs the start of the stock synchronization process for each warehouse.
        5. Synchronizes receptions and internal transfers.
        6. Updates lots to get the default Salesupply lot on new quants.
        7. Processes customer returns.
        8. Creates shipments based on Salesupply data.
        9. Performs inventory adjustments.
        Finally, it updates the last synchronization date for each shop.
        Returns:
            dict: An action to close the current window.
        """
        self.ensure_one()
        warehouse_object = self.env['stock.warehouse']
        picking_object = self.env['stock.picking']
        log_object = self.env['salesupply.log']
        quant_object = self.env['stock.quant']
        
        for shop in self.shop_ids:
            salesupply = SalesupplyRequest(shop.connection_id)
            
            warehouses = warehouse_object.search([('is_salesupply', '=', True), ('shop_id', '=', shop.id)])
            
            if self.sync_returns:
                salesupply_returns = salesupply._get_returns(shop.id_salesupply, warehouses, self.date_from_synchronization)

            if self.sync_deliveries:
                salesupply_shipments = salesupply._get_shipments(shop.id_salesupply, warehouses, self.date_from_synchronization)

            for warehouse in warehouses:
                log_object.log_info(title=_(f"Starting stock synchronization for warehouse {warehouse.name}"))
                
                # RECEPTIONS / INTERNAL TRANSFERS JL -> NL
                if self.sync_receptions:
                    self._synchronize_receptions(salesupply, warehouse)
                    self.env.cr.commit()
                    # Updating lots to get the default Salesupply lot on new quants
                    quant_object._update_salesupply_quants(warehouse, shop.default_lot_name)
                            
                # RETURNS Customers -> NL
                if self.sync_returns:
                    picking_object._return_pickings_from_salesupply(salesupply_returns[warehouse.id_salesupply])
                            
                # DELIVERIES
                if self.sync_deliveries:
                    picking_object._create_shipments_from_salesupply(salesupply, shop, warehouse, salesupply_shipments)
                
                # TODO : Inventory adjustments
                if self.do_inventory:
                    quant_object._make_inventory_from_salesupply(salesupply, warehouse)
                    quant_object._update_salesupply_quants(warehouse, shop.default_lot_name)
                
            shop.last_synchronization_date = datetime.now()
                
        return {'type': 'ir.actions.act_window_close'}
            
    def _synchronize_receptions(self, salesupply, warehouse):
        log_object = self.env['salesupply.log']
        picking_object = self.env['stock.picking']

        salesupply_receptions = salesupply._get_receptions(warehouse.shop_id.shop_owner_id_salesupply, warehouse.id_salesupply, self.date_from_synchronization)
        if 'error_message' in salesupply_receptions:
            log_object.log_error(title=_("Error while retrieving receptions"), message=salesupply_receptions['error_message'])
            return
            
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
                else:
                    log_object.log_warning(title=_(f"Couldnt find associated reception {salesupply_json_reception['OrderCode']}"))
