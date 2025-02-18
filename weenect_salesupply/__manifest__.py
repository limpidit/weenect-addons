{
    "name": "Salesupply Weenect LIT",
    "summary": "Salesupply Weenect LIT",
    "version": "16.0",
    "author": "Limpid IT",
    "depends": [
        'base',
        'sale', 
        'products',
        'stock',
    ],
    "data": [
        # Security 
        'security/ir.model.access.csv',
        # Views
        'views/product_template.xml',
        'views/salesupply_connection.xml',
        'views/salesupply_log.xml',
        'views/salesupply_sale_status.xml',
        'views/salesupply_shop.xml',
        'views/stock_picking.xml',
        'views/stock_warehouse.xml',
        # Wizard
        'wizard/salesupply_send_product_wizard.xml',
        'wizard/salesupply_stock_synchronization_wizard.xml',
        # Data
        'data/ir_cron.xml',
        'data/salesupply_sale_status.xml',
        # Menus
        'views/menu.xml',
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",    
}
