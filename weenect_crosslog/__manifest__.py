{
    "name": "Crosslog Weenect LIT",
    "summary": "Crosslog Weenect LIT",
    "version": "19.0.0.1",
    "author": "Limpid IT",
    "depends": [
        'base',
        'product',
        'stock'
    ],
    "data": [
        # Security 
        'security/ir.model.access.csv',
        # Views
        'views/crosslog_order_state.xml',
        'views/crosslog_connection.xml',
        'views/product_template.xml',
        'views/stock_picking.xml',
        'views/stock_lot_views.xml',
        'views/crosslog_log.xml',
        'views/crosslog_reception_state.xml',
        'views/crosslog_return_state.xml',
        # Wizard
        'wizard/crosslog_product_synchronization.xml',
        'wizard/crosslog_picking_synchronization.xml',
        #Data
        'data/ir_cron.xml',
        'data/crosslog_order_state.xml',
        'data/crosslog_reception_state.xml',
        'data/crosslog_return_state.xml',
        # Menus
        'views/menu.xml',
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",    
}
