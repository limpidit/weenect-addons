from . import test_partner_identification

try:
    from . import test_res_partner
except Exception:
    # odoo_test_helper is not compatible with Odoo 19 (MetaModel.module_to_models
    # was renamed to _module_to_models__). Skipping tests that depend on it.
    pass
