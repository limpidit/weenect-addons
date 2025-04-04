{
    "name": "Crosslog Weenect LIT",
    "summary": "Crosslog Weenect LIT",
    "version": "16.0",
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
        'views/crosslog_connection.xml',
        'views/product_template.xml',
        # Wizard
        'wizard/crosslog_product_synchronization.xml',
        # Menus
        'views/menu.xml',
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",    
}
