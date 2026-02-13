
from odoo import models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def copy(self, default=None):
        """
        Résolution du ticket #37879

        Lors de la dupplication d'une liste de prix :
        
        File "/home/odoo/src/odoo/odoo/addons/base/models/properties_base_definition_mixin.py", 
        line 56, in _field_to_sql return super()._field_to_sql(alias, fname, query) ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 
        File "/home/odoo/src/odoo/odoo/orm/models.py", line 2930, 
        in _field_to_sql sql = field.to_sql(self, alias) ^^^^^^^^^^^^^^^^^^^^^^^^^ 
        File "/home/odoo/src/odoo/odoo/orm/fields_relational.py", 
        line 460, in to_sql sql_field = super().to_sql(model, alias) ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 
        File "/home/odoo/src/odoo/odoo/orm/fields.py", line 1218, in to_sql 
        raise ValueError(f"Cannot convert {self} to SQL because it is not stored") 
        ValueError: Cannot convert res.partner.property_product_pricelist to SQL because it is not stored
        """
        default = dict(default or {})
        default.pop('property_product_pricelist', None)
        return super().copy(default)
