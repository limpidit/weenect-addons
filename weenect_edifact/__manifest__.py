{
    "name": "Edifact Weenect LIT",
    "summary": "Edifact Weenect LIT",
    "version": "16.0.2",
    "author": "Limpid IT",
    "depends": [
        'account',
        'account_accountant',
        'base',
        'products',
        'sale_stock',
        'account_invoice_edifact'
    ],
    "data": [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/email_template.xml',
        'data/ir_cron.xml',
        # Views
        'views/account_move.xml',
        'views/edifact_message.xml',
        'views/res_config_settings.xml',    
        'views/res_partner.xml',
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}