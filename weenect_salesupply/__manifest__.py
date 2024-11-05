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
        # Security 
        'security/ir.model.access.csv',
        # Views
        'views/res_config_settings.xml',
        'views/salesupply_shop.xml',
        # Menus
        'views/menu.xml',
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",    
}
