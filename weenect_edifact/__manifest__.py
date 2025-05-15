{
    "name": "Edifact Weenect LIT",
    "summary": "Edifact Weenect LIT",
    "version": "16.0.2",
    "author": "Limpid IT",
    "depends": [
        'account',
        'base',
        'products',
        'sale_stock',
        'account_invoice_edifact'
    ],
    "data": [
        # Data
        'data/email_template.xml',
        'data/ir_cron.xml',
        # Views
        'views/account_move.xml',
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}