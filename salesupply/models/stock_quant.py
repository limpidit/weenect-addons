from odoo import models, fields, api
import requests
import logging

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def update_stock_from_salesupply(self):
        # Configuration du logging
        logger = logging.getLogger(__name__)

        # Récupération des paramètres de configuration
        api_user = self.env['ir.config_parameter'].sudo().get_param('salesupply.api_user')
        api_password = self.env['ir.config_parameter'].sudo().get_param('salesupply.api_password')
        base_url = self.env['ir.config_parameter'].sudo().get_param('salesupply.base_url')
        location_id = int(self.env['ir.config_parameter'].sudo().get_param('salesupply.location_id'))

        # Vérification du type d'emplacement
        location = self.env['stock.location'].browse(location_id)
        if location.usage == 'view':
            raise ValueError("L'emplacement sélectionné est de type 'view'. Veuillez sélectionner un emplacement physique ou interne.")

        # Endpoint et en-têtes de la requête
        endpoint = f"{base_url}/Products"
        headers = {}

        # Authentification basique
        auth = (api_user, api_password)

        # Log de la requête envoyée
        logger.info(f"Sending request to URL: {endpoint}")
        logger.info(f"With auth: {auth}")

        # Appel à l'API Salesupply avec authentification
        response = requests.get(endpoint, headers=headers, auth=auth)

        # Log de la réponse reçue
        logger.info(f"Received response status: {response.status_code}")
        logger.info(f"Response content: {response.content}")

        if response.status_code == 200:
            stock_data = response.json()

            logger.info("Début de la mise à jour du stock dans Odoo")
            for item in stock_data:
                product_code = item.get('Code')
                qty_available = item.get('QtyAvailable', 0)

                # Recherche du produit dans Odoo
                product = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
                if product:
                    logger.info(f"Mise à jour du produit {product.name} avec la quantité disponible {qty_available}")
                    # Recherche du quant correspondant
                    quant = self.search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', location_id)
                    ], limit=1)
                    
                    if quant:
                        logger.info(f"Quant trouvé pour le produit {product.name}, mise à jour de la quantité")
                        quant.quantity = qty_available
                    else:
                        logger.info(f"Aucune quant trouvé pour le produit {product.name}, création d'une nouvelle ligne de quant")
                        self.create({
                            'product_id': product.id,
                            'location_id': location_id,
                            'quantity': qty_available,
                        })
                else:
                    logger.warning(f"Produit avec le code {product_code} non trouvé dans Odoo")
        else:
            logger.error(f"Failed to retrieve stock data: {response.content}")
            raise Exception(f"Failed to retrieve stock data: {response.content}")
