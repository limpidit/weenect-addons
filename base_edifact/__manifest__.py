{
    "name": "Base EDIFACT",
    "summary": "UN/EDIFACT/D96A utilities using pydifact parser",
    "version": "19.0.0.1",
    "category": "Tools",
    "website": "https://github.com/OCA/edi",
    "author": "ALBA Software, PlanetaTIC, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    # "preloadable": True,
    "external_dependencies": {
        "python": ["pydifact"],
        "bin": [],
    },
    "depends": [
        # for configuration
        "account",
        "partner_identification",
        "partner_identification_gln",
    ],
    "data": [],
}
