{
    "name":"EDI WEENECT",
    "summary":"EDI WEENECT",
    "version":"16.0",
    "author":"Limpid IT",
    "depends":[
        "base", "account_accountant", "products"
    ],
    "data":[
        "security/ir.model.access.csv",
        "views/account_move_edi.xml",
        "views/edi_views.xml",
        "views/menu_edi.xml","views/res_partner_edi.xml",
        "data/edi_param_data.xml",
    ],
    "installable":True,
    "application":False,
    "license":"LGPL-3",
}
