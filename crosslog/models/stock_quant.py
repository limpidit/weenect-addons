from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def update_crosslog_stock(self):
        _logger.info("Début de la mise à jour du stock Crosslog")
        
        # Récupérer les paramètres de configuration
        username = self.env['ir.config_parameter'].sudo().get_param('crosslog.stock.username')
        password = self.env['ir.config_parameter'].sudo().get_param('crosslog.stock.password')

        _logger.info(f"Utilisation de l'utilisateur: {username}")

        # Préparer la demande SOAP
        url = "http://mobile.crossdesk.com/Services/XLFlowTools.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://mobile.crossdesk.com/GetStockImage"
        }
        body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Header>
                <AuthenticationHeader xmlns="http://mobile.crossdesk.com/">
                    <Username>{username}</Username>
                    <Password>{password}</Password>
                </AuthenticationHeader>
            </soap:Header>
            <soap:Body>
                <GetStockImage xmlns="http://mobile.crossdesk.com/" />
            </soap:Body>
        </soap:Envelope>"""

        _logger.info("Envoi de la requête SOAP à Crosslog")
        
        # Envoyer la requête SOAP
        response = requests.post(url, headers=headers, data=body)
        if response.status_code == 200:
            _logger.info("Réponse reçue avec succès de Crosslog")
            # Traiter la réponse SOAP
            stock_data = self._parse_crosslog_response(response.content)
            self._update_stock(stock_data)
        else:
            # Gérer les erreurs de requête
            _logger.error(f"Erreur lors de la récupération du stock : {response.status_code}")
            raise Exception(f"Erreur lors de la récupération du stock : {response.status_code}")

    def _parse_crosslog_response(self, response_content):
        _logger.info("Début du parsing de la réponse SOAP")
        
        # Parser la réponse SOAP pour extraire les données de stock
        from lxml import etree
        root = etree.fromstring(response_content)
        namespaces = {
            'soap': "http://schemas.xmlsoap.org/soap/envelope/",
            'ns': "http://mobile.crossdesk.com/"
        }
        products = root.xpath('//ns:XLFlowStockImageProduct', namespaces=namespaces)
        stock_data = []
        for product in products:
            code = product.find('ns:Code', namespaces=namespaces).text
            quantity = int(product.find('ns:Quantity', namespaces=namespaces).text)
            stock_data.append({'code': code, 'quantity': quantity})

        _logger.info(f"Stock data parsed: {stock_data}")
        return stock_data

    def _update_stock(self, stock_data):
        _logger.info("Début de la mise à jour du stock dans Odoo")
        
        for item in stock_data:
            product = self.env['product.product'].search([('default_code', '=', item['code'])], limit=1)
            if product:
                _logger.info(f"Mise à jour du produit {product.name} avec la quantité {item['quantity']}")
                quant = self.env['stock.quant'].search([('product_id', '=', product.id)], limit=1)
                if quant:
                    _logger.info(f"Quantité trouvée pour le produit {product.name}, mise à jour de la quantité")
                    quant.quantity = item['quantity']
                else:
                    _logger.info(f"Aucune quantité trouvée pour le produit {product.name}, création d'une nouvelle ligne de quantité")
                    self.env['stock.quant'].create({
                        'product_id': product.id,
                        'location_id': self.env.ref('stock.stock_location_stock').id,
                        'quantity': item['quantity'],
                    })
            else:
                _logger.warning(f"Produit avec le code {item['code']} non trouvé dans Odoo")
