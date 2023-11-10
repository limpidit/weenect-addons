{
    "name":"Vehicules",
    "summary":"Vehicules",
    "version":"16.0",
    "author":"Limpid IT",
    "depends":[
        "base","fleet",'web_studio', "crm", "sale","rentabilite"
    ],
    "installable":True,
    "data":[
        "views/fleet_vehicle_views.xml",
        "security/ir.model.access.csv",
        "data/fleet_vehicle_options_data.xml",
        "data/sale_order_server_actions.xml",
        "data/proposition_commerciale_data.xml"
    ],
    "license":"LGPL-3",
}
