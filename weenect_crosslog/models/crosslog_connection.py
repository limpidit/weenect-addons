
from odoo import models, fields

import requests
from xml.etree import ElementTree as ET


class CrosslogConnection(models.Model):
    _name = 'crosslog.connection'
    _description = _name
    
    name = fields.Char(string="Name")

    # API Connection
    api_url = fields.Char(string="API url", required=True)
    username = fields.Char(string="API username", required=True)
    password = fields.Char(string="API password", required=True)

    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string="Warehouse")



    ################ Requests preparation ################

    def _prepare_soap_request(self, method_name, params=None):
        """Prepare the SOAP request for the given method and parameters."""

        match method_name:
            case 'ExistProduct':
                soap_body = self._prepare_exist_product_request(params['product_code'])
            case 'GetProductInformation':
                soap_body = self._prepare_get_product_information_request(params['product_code'])

        soap_request = f"""<?xml version="1.0" encoding="UTF-8"?>
        <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:mob="http://mobile.crossdesk.com/">
            <soap:Header>
                <mob:AuthenticationHeader>
                    <mob:Username>{self.username}</mob:Username>
                    <mob:Password>{self.password}</mob:Password>
                </mob:AuthenticationHeader>
            </soap:Header>
            <soap:Body>
                {soap_body}
            </soap:Body>
        </soap:Envelope>"""
        return soap_request

    def _prepare_exist_product_request(self, product_code):
        """Prepare the request for the ExistProduct method."""
        return f"""<mob:ExistProduct>
            <mob:productCode>{product_code}</mob:productCode>
        </mob:ExistProduct>"""

    def _prepare_get_product_information_request(self, product_code):
        """Prepare the request for the GetProductInformation method."""
        return f"""<mob:GetProductInformation>
            <mob:productCode>{product_code}</mob:productCode>
        </mob:GetProductInformation>"""



    ################ Requests execution ################

    def _send_soap_request(self, soap_request):
        """Send the SOAP request to the API and return the response."""
        headers = {'Content-Type': 'text/xml; charset=utf-8'}
        try:
            response = requests.post(self.api_url, data=soap_request, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            _logger.error(f"SOAP request failed: {str(e)}")
            raise UserError(_("Failed to connect to Crosslog API"))

    def _parse_soap_response(self, response_text, method_name):
        try:
            root = ET.fromstring(response_text)
            ns = {'ns': 'http://mobile.crossdesk.com/'}
            
            match method_name:
                case 'ExistProduct':
                    result = root.find('.//ns:ExistProductResult', ns)
                    return result.text.lower() == 'true'
                case 'GetProductInformation':
                    result = root.find('.//ns:GetProductInformationResult', ns)
                    return {
                        'code': result.find('ns:Code', ns).text,
                        'barcode': result.find('ns:BarCode', ns).text,
                        'available_qty': float(result.find('ns:AvailableQuantity', ns).text),
                        'reserved_qty': float(result.find('ns:ReservedQuantity', ns).text),
                        'receipt_qty': float(result.find('ns:ReceiptQuantity', ns).text),
                        'rubbish_qty': float(result.find('ns:RubbishQuantity', ns).text),
                        'security_qty': float(result.find('ns:SecurityQuantity', ns).text),
                    }
                
        except ET.ParseError as e:
            _logger.error(f"Failed to parse SOAP response: {str(e)}")
            raise UserError(_("Invalid SOAP response format"))



    ################ Business methods ################

    def process_exist_item_request(self, product_code):
        """Process the ExistProduct request and return the result."""
        soap_request = self._prepare_soap_request('ExistProduct', {'product_code': product_code})
        response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'ExistProduct')
        return result

    def process_get_product_information_request(self, product_code):
        """Process the GetProductInformation request and return the result."""
        soap_request = self._prepare_soap_request('GetProductInformation', {'product_code': product_code})
        response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'GetProductInformation')
        return result