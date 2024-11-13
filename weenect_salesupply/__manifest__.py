{
    "name": "Salesupply Weenect LIT",
    "summary": "Salesupply Weenect LIT",
    "version": "16.0",
    "author": "Limpid IT",
    "depends": [
        'base',
        'stock'
    ],
    "data": [
        # Data
        'data/ir_cron.xml',
        # Security 
        'security/ir.model.access.csv',
        # Views
        'views/salesupply_connection.xml',
        'views/salesupply_shop.xml',
        'views/salesupply_synchronization.xml',
        'views/stock_warehouse.xml',
        # Menus
        'views/menu.xml',
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",    
}
