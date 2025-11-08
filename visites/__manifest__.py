{
    "name":"Visites LimpidIT",
    "summary":"Visites LimpidIT",
    "version":"19.0.0.1",
    "author":"Limpid IT",
    "depends":["base","crm","mail","base_geolocalize","web_map"
    ],
    "data": [
        'security/groups.xml',
        "security/ir.model.access.csv",
        'views/visite.xml',
        'views/visite_menu.xml',
        'views/res_partner_views.xml',
        'views/generate_visites_wizard.xml',
        'views/tournee_views.xml'
    ],
    "installable":True,
    "application":True,
    "license":"LGPL-3",
}
