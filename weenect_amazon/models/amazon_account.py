from odoo import fields, models

# Codes pays considérés comme "UK"
UK_COUNTRY_CODES = {'GB'}

# Codes pays considérés comme "USA"
US_COUNTRY_CODES = {'US'}


class AmazonAccount(models.Model):
    _inherit = 'amazon.account'

    fbm_warehouse_eu_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string="Entrepôt FBM Europe",
        help="Entrepôt utilisé pour les commandes FBM Amazon avec une adresse de livraison en Europe continentale.",
        check_company=True,
    )
    fbm_warehouse_uk_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string="Entrepôt FBM UK",
        help="Entrepôt utilisé pour les commandes FBM Amazon avec une adresse de livraison au Royaume-Uni.",
        check_company=True,
    )
    fbm_warehouse_us_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string="Entrepôt FBM USA",
        help="Entrepôt utilisé pour les commandes FBM Amazon avec une adresse de livraison aux États-Unis.",
        check_company=True,
    )

    def _get_fbm_warehouse(self, order_data):
        """Retourne l'entrepôt à affecter à une commande FBM selon le pays de livraison.

        :param dict order_data: Les données de la commande Amazon.
        :return: L'entrepôt correspondant, ou un recordset vide si non configuré.
        :rtype: record of `stock.warehouse`
        """
        self.ensure_one()
        country_code = order_data.get('ShippingAddress', {}).get('CountryCode', '')
        if country_code in UK_COUNTRY_CODES:
            return self.fbm_warehouse_uk_id
        elif country_code in US_COUNTRY_CODES:
            return self.fbm_warehouse_us_id
        else:
            return self.fbm_warehouse_eu_id

    def _prepare_order_values(self, order_data):
        order_vals = super()._prepare_order_values(order_data)
        fulfillment_channel = order_data.get('FulfillmentChannel')
        if fulfillment_channel == 'MFN':
            warehouse = self._get_fbm_warehouse(order_data)
            if warehouse:
                order_vals['warehouse_id'] = warehouse.id
        return order_vals
