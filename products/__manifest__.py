{
    "name":"Products Weenect LIT",
    "summary":"Products Weenect LIT",
    "version": "19.0.1.0.0",
    "author":"Limpid IT",
    "depends":[
        "base",'web_studio', "crm", "sale", "contacts", "stock"
    ],
    "installable":True,
    "application":True,
    "data":[
        "views/product_template_views.xml",
        "views/res_partner_views.xml",
        "views/traceurs_sav.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "security/ir.model.access.csv",
    ],
    "license":"LGPL-3",
}