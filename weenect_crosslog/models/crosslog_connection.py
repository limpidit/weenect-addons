
from odoo import models, fields, api
from datetime import datetime
import requests
from xml.etree import ElementTree as ET
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class CrosslogConnection(models.Model):
    _name = 'crosslog.connection'
    _description = _name
    
    name = fields.Char(string="Name")

    # API Connection
    api_url = fields.Char(string="API url", required=True)
    username = fields.Char(string="API username", required=True)
    password = fields.Char(string="API password", required=True)

    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string="Warehouse")
    crosslog_order_state_ids = fields.Many2many(comodel_name='crosslog.order.state', string="Crosslog order states corresponding to 'shipped'")
    crosslog_reception_state_ids = fields.Many2many(comodel_name='crosslog.reception.state', string="Crosslog receptions status corresponding to 'receveid'")
    crosslog_return_state_ids = fields.Many2many(comodel_name='crosslog.return.state', string="Crosslog returns status corresponding to 'receveid'")

    default_delivery_partner_id = fields.Many2one(comodel_name='res.partner', string="Default delivery user")



    ################ Requests preparation ################

    def _prepare_soap_request(self, method_name, params=None):
        """Prepare the SOAP request for the given method and parameters."""

        if method_name == 'ExistProduct':
            soap_body = self._prepare_exist_product_request(params['product_code'])
        elif method_name == 'GetProductInformation':
            soap_body = self._prepare_get_product_information_request(params['product_code'])
        elif method_name == 'GetCustomerOrdersUpdated':
            soap_body = self._prepare_get_customer_orders_updated_request()
        elif method_name == 'GetSupplierOrdersUpdated':
            soap_body = self._prepare_get_supplier_orders_updated_request()
        elif method_name == 'GetCustomerReturnsUpdated':
            soap_body = self._prepare_get_customer_returns_updated_request()

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

    @api.model
    def _prepare_exist_product_request(self, product_code):
        """Prepare the request for the ExistProduct method."""
        return f"""<mob:ExistProduct>
            <mob:productCode>{product_code}</mob:productCode>
        </mob:ExistProduct>"""

    @api.model
    def _prepare_get_product_information_request(self, product_code):
        """Prepare the request for the GetProductInformation method."""
        return f"""<mob:GetProductInformation>
            <mob:productCode>{product_code}</mob:productCode>
        </mob:GetProductInformation>"""

    @api.model
    def _prepare_get_customer_orders_updated_request(self):
        """Prepare the request for the GetCustomerOrdersUpdated method."""
        return f"""<mob:GetCustomerOrdersUpdated></mob:GetCustomerOrdersUpdated>"""

    @api.model
    def _prepare_get_supplier_orders_updated_request(self):
        """Prepare the request for the GetSupplierOrdersUpdated method."""
        return f"""<mob:GetSupplierOrdersUpdated></mob:GetSupplierOrdersUpdated>"""

    @api.model
    def _prepare_get_customer_returns_updated_request(self):
        """Prepare the request for the GetSupplierOrdersUpdated method."""
        return f"""<mob:GetCustomerReturnsUpdated></mob:GetCustomerReturnsUpdated>"""


    ################ Requests execution ################

    def _send_soap_request(self, soap_request):
        """Send the SOAP request to the API and return the response."""
        headers = {'Content-Type': 'text/xml; charset=utf-8'}
        try:
            response = requests.post(self.api_url, data=soap_request, headers=headers, timeout=60)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            _logger.error(f"SOAP request failed: {str(e)}")
            raise UserError(_("Failed to connect to Crosslog API"))

    @api.model
    def _parse_soap_response(self, response_text, method_name):
        try:
            root = ET.fromstring(response_text)
            ns = {'ns': 'http://mobile.crossdesk.com/'}
            
            if method_name == 'ExistProduct':
                return self._parse_exist_item_response(root, ns)
            elif method_name == 'GetProductInformation':
                return self._parse_get_product_information_response(root, ns)
            elif method_name == 'GetCustomerOrdersUpdated':
                return self._parse_get_customer_orders_updated_response(root, ns)
            elif method_name == 'GetSupplierOrdersUpdated':
                return self._parse_get_supplier_orders_updated_response(root, ns)
            elif method_name == 'GetCustomerReturnsUpdated':
                return self._parse_get_customer_returns_updated_response(root, ns)

        except ET.ParseError as e:
            _logger.error(f"Failed to parse SOAP response: {str(e)}")
            raise UserError(_("Invalid SOAP response format"))


    def _parse_exist_item_response(self, root, ns):
        result = root.find('.//ns:ExistProductResult', ns)
        return result.text.lower() == 'true'

    def _parse_get_product_information_response(self, root, ns):
        result = root.find('.//ns:GetProductInformationResult', ns)
        data = {
            'code': self._txt(result, 'ns:Code', ns),
            'barcode': self._txt(result, 'ns:BarCode', ns),
            'available_qty': (self._txt(result, 'ns:AvailableQuantity', ns)),
            'reserved_qty': (self._txt(result, 'ns:ReservedQuantity', ns)),
            'receipt_qty': (self._txt(result, 'ns:ReceiptQuantity', ns)),
            'rubbish_qty': (self._txt(result, 'ns:RubbishQuantity', ns)),
            'security_qty': (self._txt(result, 'ns:SecurityQuantity', ns)),
            'lots': [],
        }
        lots = result.findall('.//ns:XLFlowProductLotReturnEntity', ns)
        for lot in lots:
            data['lots'].append({
                'lot_number': self._txt(lot, 'ns:LotNumber', ns),
                'expired_date': self._txt(lot, 'ns:ExpiredDate', ns),
                'quantity': (self._txt(lot, 'ns:Quantity', ns)),
            })
        return data


    def _parse_get_customer_orders_updated_response(self, root, ns):
        orders = root.findall('.//ns:XLFlowCustomerOrderReturnEntity', ns)
        data = []
        for order in orders:
            order_dict = {
                'order_number': self._txt(order, 'ns:OrderNumber', ns),
                'state': self._txt(order, 'ns:State', ns),
                'order_lines': [],
            }
            lines_parent = order.find('ns:OrderLines', ns)
            if lines_parent is not None:
                for line in lines_parent.findall('ns:XLFlowOrderLineReturnEntity', ns):
                    line_dict = {
                        'code': self._txt(line, 'ns:Code', ns),
                        'initial_qty': (self._txt(line, 'ns:InitialQuantity', ns)),
                        'reserved_qty': (self._txt(line, 'ns:ReservedQuantity', ns)),
                        'returned_qty': (self._txt(line, 'ns:ReturnedQuantity', ns)),
                        'sent_qty': (self._txt(line, 'ns:SentQuantity', ns)),
                        'lots': [],
                    }
                    lots_parent = line.find('ns:OrderLineProductLots', ns)
                    if lots_parent is not None:
                        for lot in lots_parent.findall('ns:XLFlowOrderLineProductLotReturnEntity', ns):
                            line_dict['lots'].append({
                                'lot_code': self._txt(lot, 'ns:ProductLotCode', ns),
                                'quantity': (self._txt(lot, 'ns:Quantity', ns)),
                            })
                    order_dict['order_lines'].append(line_dict)
            data.append(order_dict)
        return data


    def _parse_get_supplier_orders_updated_response(self, root, ns):
        orders = root.findall('.//ns:XLFlowSupplierOrderReturnEntity', ns)
        data = []
        for order in orders:
            order_dict = {
                'order_number': self._txt(order, 'ns:OrderNumber', ns),
                'state': self._txt(order, 'ns:State', ns),
                'arrival_date': self._txt(order, 'ns:ArrivalDate', ns),
                'order_lines': [],
            }
            lines_parent = order.find('ns:OrderLines', ns)
            if lines_parent is not None:
                for line in lines_parent.findall('ns:XLFlowSupplierOrderLineReturnEntity', ns):
                    line_dict = {
                        'code': self._txt(line, 'ns:Code', ns),
                        'initial_qty': (self._txt(line, 'ns:InitialQuantity', ns)),
                        'receipt_qty': (self._txt(line, 'ns:ReceiptQuantity', ns))
                    }
                    order_dict['order_lines'].append(line_dict)
            data.append(order_dict)
        return data

    def _parse_get_customer_returns_updated_response(self, root, ns):
        orders = root.findall('.//ns:XLFlowCustomerReturnReturnEntity', ns)
        data = []
        for order in orders:
            order_dict = {
                'return_number': self._txt(order, 'ns:ReturnNumber', ns),
                'order_number': self._txt(order, 'ns:OrderNumber', ns),
                'state': self._txt(order, 'ns:State', ns),
                'order_lines': [],
            }
            lines_parent = order.find('ns:ReturnLines', ns)
            if lines_parent is not None:
                for line in lines_parent.findall('ns:XLFlowCustomerReturnLineReturnEntity', ns):
                    line_dict = {
                        'code': self._txt(line, 'ns:Code', ns),
                        'receipt_qty': (self._txt(line, 'ns:ReceiptQuantity', ns))
                    }
                    order_dict['order_lines'].append(line_dict)
            data.append(order_dict)
        return data
        


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

    def process_get_customer_orders_updated_request(self):
        """Process the GetCustomerOrdersUpdated request and return the result."""
        soap_request = self._prepare_soap_request('GetCustomerOrdersUpdated')
        response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'GetCustomerOrdersUpdated')
        return result

    def process_get_supplier_orders_updated_request(self):
        """Process the GetSupplierOrdersUpdated request and return the result."""
        soap_request = self._prepare_soap_request('GetSupplierOrdersUpdated')
        response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'GetSupplierOrdersUpdated')
        return result

    def process_get_customer_returns_updated_request(self):
        """Process the GetCustomerReturnsUpdated request and return the result."""
        soap_request = self._prepare_soap_request('GetCustomerReturnsUpdated')
        response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'GetCustomerReturnsUpdated')
        return result


    ############## Utils ################

    def _txt(self, node, path, ns, default=None):
        """Retourne node.find(path, ns).text en safe."""
        el = node.find(path, ns)
        return el.text.strip() if (el is not None and el.text is not None) else default