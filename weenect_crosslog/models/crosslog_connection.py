
from odoo import models, fields, api, _
from datetime import datetime
import requests
from xml.etree import ElementTree as ET
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare
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
    is_used_for_cron = fields.Boolean(string="Use it for scheduled synchronization", default=False)

    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string="Warehouse")
    crosslog_order_state_ids = fields.Many2many(comodel_name='crosslog.order.state', string="Crosslog order states corresponding to 'shipped'")
    crosslog_reception_state_ids = fields.Many2many(comodel_name='crosslog.reception.state', string="Crosslog receptions status corresponding to 'receveid'")
    crosslog_return_state_ids = fields.Many2many(comodel_name='crosslog.return.state', string="Crosslog returns status corresponding to 'receveid'")

    default_delivery_partner_id = fields.Many2one(comodel_name='res.partner', string="Default delivery user")

    batch_threshold = fields.Integer(string="Maximum unprocessed pickings", default=5, help="Maximum number of unprocessed deliveries/receptions/returns allowed for batch validation")


    @api.constrains('is_used_for_cron')
    def _check_unique_active(self):
        for record in self:
            if record.is_used_for_cron:
                domain = [
                    ('is_used_for_cron', '=', True),
                    ('id', '!=', record.id),
                ]
                if self.search_count(domain):
                    raise ValidationError(
                        "Only one Crosslog connection can be used for scheduled synchronization."
                    )

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
        elif method_name == 'ValidateSupplierOrdersUpdated':
            soap_body = self._prepare_validate_supplier_orders_updated_request()
        elif method_name == 'ValidateCustomerOrdersUpdated':
            soap_body = self._prepare_validate_customer_orders_updated_request()
        elif method_name == 'ValidateCustomerReturnsUpdated':
            soap_body = self._prepare_validate_customer_returns_updated_request()

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
        """Prepare the request for the GetCustomerReturnsUpdated method."""
        return f"""<mob:GetCustomerReturnsUpdated></mob:GetCustomerReturnsUpdated>"""

    @api.model
    def _prepare_validate_supplier_orders_updated_request(self):
        """Prepare the request for the ValidateSupplierOrdersUpdated method."""
        return f"""<mob:ValidateSupplierOrdersUpdated></mob:ValidateSupplierOrdersUpdated>"""

    @api.model
    def _prepare_validate_customer_orders_updated_request(self):
        """Prepare the request for the ValidateCustomerOrdersUpdated method."""
        return f"""<mob:ValidateCustomerOrdersUpdated></mob:ValidateCustomerOrdersUpdated>"""

    @api.model
    def _prepare_validate_customer_returns_updated_request(self):
        """Prepare the request for the ValidateCustomerOrdersUpdated method."""
        return f"""<mob:ValidateCustomerReturnsUpdated></mob:ValidateCustomerReturnsUpdated>"""


    ################ Requests execution ################

    def _send_soap_request(self, soap_request):
        """Send the SOAP request to the API and return the response."""
        headers = {'Content-Type': 'text/xml; charset=utf-8'}
        try:
            response = requests.post(self.api_url, data=soap_request, headers=headers, timeout=60)
            response.raise_for_status()
            return response.status_code, response.text
        except requests.exceptions.RequestException as e:
            _logger.error(f"SOAP request failed: {str(e)}")
            raise UserError(_("Failed to connect to Crosslog API"))

    @api.model
    def _parse_soap_response(self, response_text, method_name, status_code = 200):
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
        status_code, response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'ExistProduct')
        return result

    def process_get_product_information_request(self, product_code):
        """Process the GetProductInformation request and return the result."""
        soap_request = self._prepare_soap_request('GetProductInformation', {'product_code': product_code})
        status_code, response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'GetProductInformation')
        return result

    def process_get_customer_orders_updated_request(self):
        """Process the GetCustomerOrdersUpdated request and return the result."""
        soap_request = self._prepare_soap_request('GetCustomerOrdersUpdated')
        status_code, response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'GetCustomerOrdersUpdated')
        return result

    def process_get_supplier_orders_updated_request(self):
        """Process the GetSupplierOrdersUpdated request and return the result."""
        soap_request = self._prepare_soap_request('GetSupplierOrdersUpdated')
        status_code, response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'GetSupplierOrdersUpdated')
        return result

    def process_get_customer_returns_updated_request(self):
        """Process the GetCustomerReturnsUpdated request and return the result."""
        soap_request = self._prepare_soap_request('GetCustomerReturnsUpdated')
        status_code, response_text = self._send_soap_request(soap_request)
        result = self._parse_soap_response(response_text, 'GetCustomerReturnsUpdated')
        return result

    def process_validate_suppplier_orders_updated_request(self):
        """Process the ValidateSupplierOrdersUpdated request and return the result."""
        soap_request = self._prepare_soap_request('ValidateSupplierOrdersUpdated')
        status_code, response_text = self._send_soap_request(soap_request)
        return status_code

    def process_validate_customer_orders_updated_request(self):
        """Process the ValidateCustomerOrdersUpdated request and return the result."""
        soap_request = self._prepare_soap_request('ValidateCustomerOrdersUpdated')
        status_code, response_text = self._send_soap_request(soap_request)
        return status_code

    def process_validate_customer_returns_updated_request(self):
        """Process the ValidateCustomerReturnsUpdated request and return the result."""
        soap_request = self._prepare_soap_request('ValidateCustomerReturnsUpdated')
        status_code, response_text = self._send_soap_request(soap_request)
        return status_code


    ############## Utils ################

    def _txt(self, node, path, ns, default=None):
        """Retourne node.find(path, ns).text en safe."""
        el = node.find(path, ns)
        return el.text.strip() if (el is not None and el.text is not None) else default


    ############ Synchronisation methods ################

    def synchronize_pickings(self, *, sync_deliveries=False, sync_receptions=False, sync_returns=False):
        """Synchronize pickings with Crosslog."""
        if not sync_deliveries and not sync_receptions and not sync_returns:
            raise UserError(_("Please select at least one synchronization option (deliveries, receptions or returns)."))
        if sync_deliveries:
            self.synchronize_deliveries()
        if sync_receptions:
            self.synchronize_receptions()
        if sync_returns:
            self.synchronize_returns()
    

    def synchronize_deliveries(self):
        """Synchronize deliveries with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']

        warehouse = self.warehouse_id

        partner = self.default_delivery_partner_id
        shipping_status = self.crosslog_order_state_ids
        unvalid_pickings_limit = float(self.batch_threshold or 5)

        try:
            log_object.log_info(title=_(f"Orders synchronization started."))
            deliveries = self.process_get_customer_orders_updated_request()
            shipping_codes = {str(c) for c in shipping_status.mapped('code') if c is not None}
            unvalid_pickings = []

            for delivery in deliveries:
                try:
                    state = delivery.get('state')
                    order_number = delivery.get('order_number')
                    if not state:
                        unvalid_pickings.append(order_number)
                        log_object.log_warning(title=_("Delivery state is missing in the response for Crosslog order %s.") % (order_number))
                        continue
                    is_shipping = state in shipping_codes

                    picking = picking_object.search([
                        ('crosslog_code', '=', delivery.get('order_number')),
                        ('picking_type_id.code', '=', 'outgoing'),
                        ('location_id', '=', warehouse.lot_stock_id.id),
                        ('crosslog_synchronized', '=', True)
                    ], limit=1)

                    if is_shipping:
                        if picking:
                            if picking.state not in ['done', 'cancel']:
                                if not picking.try_make_picking_ready(order_number):
                                    unvalid_pickings.append(order_number)
                                    continue
                                if not picking.try_validate_picking(order_number):
                                    unvalid_pickings.append(order_number)
                                    continue
                        else:
                            new_picking = picking_object.create_delivery(delivery, warehouse, partner)
                            if new_picking:
                                if not new_picking.try_make_picking_ready(order_number):
                                    unvalid_pickings.append(order_number)
                                    continue
                                if not new_picking.try_validate_picking(order_number):
                                    unvalid_pickings.append(order_number)
                                    continue
                            else:
                                unvalid_pickings.append(order_number)
                
                except Exception as e:
                    log_object.log_error(title=_("Error during synchronisation of Crosslog order %s.") % (order_number), message=str(e))
            
            log_object.log_info(title=_(f"Orders synchronization successfully completed."))
        
            self.batch_process(unvalid_pickings, unvalid_pickings_limit, deliveries, 'ValidateCustomerOrdersUpdated')

        except Exception as e:
            log_object.log_error(title=_(f"Error during orders synchronization."), message=str(e))

    
    def synchronize_receptions(self):
        """Synchronize receptions with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']
        product_product_object = self.env['product.product']

        warehouse = self.warehouse_id
        arrival_status = self.crosslog_reception_state_ids
        unvalid_pickings_limit = float(self.batch_threshold)

        try:
            log_object.log_info(title=_(f"Receptions synchronization started."))
            receptions = self.process_get_supplier_orders_updated_request()
            arrival_codes = {str(c) for c in arrival_status.mapped('code') if c is not None}
            unvalid_pickings = []

            for reception in receptions:
                try:
                    skip_reception = False
                    state = reception.get('state')
                    order_number = reception.get('order_number')

                    if not state:
                        log_object.log_warning(title=_("Reception state is missing in the response for Crosslog reception number %s.") % (order_number))
                        continue
                    if not order_number:
                        log_object.log_warning(title=_(f"Reception order number is missing in the response."))
                        continue
                    is_arrived = state in arrival_codes

                    if is_arrived:
                        picking = picking_object.search([
                            ('origin', '=', order_number),
                            ('picking_type_id.code', '=', 'internal'),
                            ('location_dest_id', '=', warehouse.lot_stock_id.id),
                            ('crosslog_synchronized', '=', False),
                            ('state', '=', 'assigned')
                        ], limit=1)

                        if not picking:
                            picking_synchronized = picking_object.search([
                                ('origin', '=', order_number),
                                ('picking_type_id.code', '=', 'internal'),
                                ('location_dest_id', '=', warehouse.lot_stock_id.id),
                                ('crosslog_synchronized', '=', True),
                                ('state', '=', 'done')
                            ], limit=1)
                            if not picking_synchronized:
                                unvalid_pickings.append(order_number)
                                log_object.log_warning(title=_("Reception with Crosslog code %s not found in Odoo or already validated.") % (order_number))
                                continue
                            else:
                                log_object.log_info(title=_("Reception with Crosslog code %s already validated.") % (order_number))
                                continue

                        lines = reception.get('order_lines') or []
                        if not lines:
                            unvalid_pickings.append(order_number)
                            log_object.log_warning(title=_("Reception %s not validated.") % (picking.name), message=_("No order lines from Crosslog.\nCrosslog origin : %s.") % (order_number))
                            continue

                        for line in lines:
                            product_code = line['code']
                            product = product_product_object.search([('default_code', '=', product_code), ('available_on_crosslog', '=', True)], limit=1)
                            receipt_qty = float(line.get('receipt_qty') or 0.0)
                            
                            if not product:
                                skip_reception = True
                                unvalid_pickings.append(order_number)
                                log_object.log_warning(title=_("Reception %s not validated.") % (picking.name), message=_("The product %s does not exist in Odoo or is not synchronised with Crosslog.\nCrosslog origin : %s.") % (product_code, order_number))
                                break
                            
                            move = picking.move_ids.filtered(lambda m: m.product_id.id == product.id)
                            if move:
                                expected_qty = move.product_uom_qty
                                if expected_qty != receipt_qty:
                                    skip_reception = True
                                    unvalid_pickings.append(order_number)
                                    log_object.log_warning(title=_("Reception %s not validated.") % (picking.name), message=_("Quantity mismatch for product %s.\nExpected quantity in Odoo : %s. Received quantity in Crosslog : %s.\nCrosslog origin : %s.") % (product.name, expected_qty, receipt_qty, order_number))
                                    break
                            
                                move._action_confirm()
                                move._action_assign()

                            else:
                                skip_reception = True
                                unvalid_pickings.append(order_number)
                                log_object.log_warning(title=_("Reception %s not validated.") % (picking.name), message=_("No line on transfer %s with product %s matched.\nCrosslog origin : %s.") % (picking.name, product_code, order_number))
                                break

                        if skip_reception:
                            continue

                        if not picking.try_make_picking_ready(order_number):
                            unvalid_pickings.append(order_number)
                            continue
                        if not picking.try_validate_picking(order_number):
                            unvalid_pickings.append(order_number)
                            continue

                        picking.crosslog_synchronized = True
                        picking.crosslog_code = order_number

                except Exception as e:
                    log_object.log_error(
                        title=_("Error during synchronization of Crosslog reception %s.") % (order_number),
                        message=str(e)
                    )

            log_object.log_info(title=_(f"Receptions synchronization successfully completed."))

            self.batch_process(unvalid_pickings, unvalid_pickings_limit, receptions, 'ValidateSupplierOrdersUpdated')

        except Exception as e:
            log_object.log_error(title=_(f"Error during receptions synchronization."), message=str(e))

    
    def synchronize_returns(self):
        """Synchronize returns with Crosslog."""
        self.ensure_one()
        picking_object = self.env['stock.picking']
        log_object = self.env['crosslog.log']

        warehouse = self.warehouse_id
        return_status = self.crosslog_return_state_ids
        unvalid_pickings_limit = float(self.batch_threshold)

        try:
            log_object.log_info(title=_(f"Returns synchronization started."))
            returns = self.process_get_customer_returns_updated_request()
            return_codes = {str(c) for c in return_status.mapped('code') if c is not None}
            valid_returns = [
                re for re in returns
                if re.get('state') in return_codes
            ]
            unvalid_pickings = []

            for re in valid_returns:
                try:
                    return_number = re.get('return_number') or []
                    order_number = re.get('order_number') or []
                    lines = re.get('order_lines') or []

                    if not return_number:
                        log_object.log_warning(title=_(f"Return number is missing in the response."))
                        unvalid_pickings.append("Unknow")
                        continue
                    if not order_number:
                        log_object.log_warning(title=_("Return %s not synchronized") % (return_number), message=_(f"Order number is missing in the response."))
                        unvalid_pickings.append(return_number)
                        continue
                    if not lines:
                        log_object.log_warning(title=_("Return %s not synchronized") % (return_number), message=_(f"No order lines from Crosslog"))
                        unvalid_pickings.append(return_number)
                        continue
                    
                    exist_return = picking_object.search([
                        ('crosslog_code', '=', return_number),
                        ('picking_type_id.code', '=', 'incoming'),
                        ('location_dest_id', '=', warehouse.lot_stock_id.id),
                        ('crosslog_synchronized', '=', True)
                    ])
                    if exist_return:
                        log_object.log_info(title=_("Return %s is already synchronized in Odoo.") % (return_number))
                        continue

                    delivery = picking_object.search([
                        ('crosslog_code', '=', order_number),
                        ('picking_type_id.code', '=', 'outgoing'),
                        ('location_id', '=', warehouse.lot_stock_id.id),
                        ('crosslog_synchronized', '=', True),
                        ('state', '=', 'done')
                    ], limit=1)

                    if not delivery:
                        log_object.log_warning(title=_("Return %s not synchronized") % (return_number), message=_("Synchronized done delivery %s not found in Odoo.") % (order_number))
                        unvalid_pickings.append(return_number)
                        continue

                    return_picking = picking_object.create_return(lines, return_number, order_number, delivery)
                    if not return_picking:
                        unvalid_pickings.append(return_number)
                        continue
                    else:
                        return_picking.move_ids._action_confirm()

                    if not return_picking.try_validate_picking(return_number):
                        unvalid_pickings.append(return_number)
                        continue

                    return_picking.crosslog_synchronized = True
                    return_picking.crosslog_code = return_number

                except Exception as e:
                    log_object.log_error(title=_("Error during synchronization of return %s.") % (return_number), message=str(e))
            
            log_object.log_info(title=_(f"Returns synchronization successfully completed."))

            self.batch_process(unvalid_pickings, unvalid_pickings_limit, returns, 'ValidateCustomerReturnsUpdated')

        except Exception as e:
            log_object.log_error(title=_(f"Error during returns synchronization."), message=str(e))


    def synchronize_products(self, synchronize_stock=False):
        """Backend sync products. Cron-safe + wizard-safe."""
        self.ensure_one()

        product_object = self.env['product.product']
        quant_object = self.env['stock.quant']
        lot_object = self.env['stock.lot']
        log_object = self.env['crosslog.log']

        warehouse = self.warehouse_id
        if not warehouse or not warehouse.lot_stock_id:
            log_object.log_error(title=_("Products synchronization failed."), message=_("No warehouse/stock location configured on Crosslog connection."))
            return

        existing_quants = quant_object.browse()
        quant_vals = []

        log_object.log_info(title=_("Products synchronization started."))

        for product in product_object.search([]):
            default_code = (product.default_code or "").strip()
            if not default_code:
                continue

            try:
                exists = self.process_exist_item_request(default_code)
            except Exception as e:
                log_object.log_error(
                    title=_("Crosslog check failed for %s") % default_code,
                    message=str(e),
                )
                continue

            if not exists:
                product.available_on_crosslog = False
                continue

            product.available_on_crosslog = True

            if not synchronize_stock:
                continue

            try:
                product_info = self.process_get_product_information_request(default_code) or {}
            except Exception as e:
                log_object.log_error(
                    title=_("Crosslog product info failed for %s") % default_code,
                    message=str(e),
                )
                continue

            if product.tracking == 'lot':
                lots_data = product_info.get('lots') or []
                if not lots_data:
                    log_object.log_warning(
                        title=_("No lot retrieved for %s (%s), skipping.") % (product.display_name, default_code)
                    )
                    continue

                for lot_info in lots_data:
                    lot_name = (lot_info.get('lot_number') or '').strip()
                    qty = float(lot_info.get('quantity') or 0.0)

                    if not lot_name:
                        log_object.log_warning(title=_("Lot without name for %s, ignored.") % default_code)
                        continue

                    lot = lot_object.search([('name', '=', lot_name), ('product_id', '=', product.id)], limit=1)
                    if not lot:
                        lot = lot_object.create({
                            'name': lot_name,
                            'product_id': product.id,
                            'available_on_crosslog': True,
                        })
                    else:
                        lot.available_on_crosslog = True

                    existing_quant = quant_object.search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', warehouse.lot_stock_id.id),
                        ('lot_id', '=', lot.id),
                    ], limit=1)

                    if existing_quant:
                        if float_compare(existing_quant.inventory_quantity, qty, precision_rounding=product.uom_id.rounding) != 0:
                            existing_quant.write({'inventory_quantity': qty})
                            existing_quants |= existing_quant
                    else:
                        quant_vals.append({
                            'product_id': product.id,
                            'location_id': warehouse.lot_stock_id.id,
                            'lot_id': lot.id,
                            'inventory_quantity': qty,
                        })
            else:
                available = float(product_info.get('available_qty') or 0.0)
                reserved = float(product_info.get('reserved_qty') or 0.0)
                qty = available + reserved

                existing_quant = quant_object.search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', warehouse.lot_stock_id.id),
                    ('lot_id', '=', False),
                ], limit=1)

                if existing_quant:
                    if float_compare(existing_quant.inventory_quantity, qty, precision_rounding=product.uom_id.rounding) != 0:
                        existing_quant.write({'inventory_quantity': qty})
                        existing_quants |= existing_quant
                else:
                    quant_vals.append({
                        'product_id': product.id,
                        'location_id': warehouse.lot_stock_id.id,
                        'inventory_quantity': qty,
                    })

        if quant_vals:
            existing_quants |= quant_object.create(quant_vals)

        if existing_quants:
            if 'inventory_diff_quantity' in existing_quants._fields:
                quants_to_apply = existing_quants.filtered(
                    lambda q: float_compare(
                        q.inventory_diff_quantity, 0.0,
                        precision_rounding=q.product_id.uom_id.rounding
                    ) != 0
                )
            else:
                quants_to_apply = existing_quants.filtered(
                    lambda q: float_compare(
                        (q.inventory_quantity - q.quantity), 0.0,
                        precision_rounding=q.product_id.uom_id.rounding
                    ) != 0
                )

            if quants_to_apply:
                quants_to_apply.action_apply_inventory()

        log_object.log_info(title=_("Products synchronization completed."))


    def validate_batch(self, batch_name):
        if batch_name == 'ValidateSupplierOrdersUpdated':
            return self.process_validate_suppplier_orders_updated_request()
        if batch_name == 'ValidateCustomerOrdersUpdated':
            return self.process_validate_customer_orders_updated_request()
        if batch_name == 'ValidateCustomerReturnsUpdated':
            return self.process_validate_customer_returns_updated_request()
    
    
    def batch_process(self, unvalid_pickings, unvalid_pickings_limit, pickings, batch_name):
        details = ", ".join(unvalid_pickings) if unvalid_pickings else _("Nothing")
        picking_name = ""
        log_object = self.env['crosslog.log']

        if batch_name == 'ValidateSupplierOrdersUpdated':
            picking_name = "commandes fournisseurs"
        if batch_name == 'ValidateCustomerOrdersUpdated':
            picking_name = "commandes clients"
        if batch_name == 'ValidateCustomerReturnsUpdated':
            picking_name = "retours"

        if len(unvalid_pickings) <= unvalid_pickings_limit:
            if len(pickings) > 0:
                result = self.validate_batch(batch_name)
                if result == 200:
                    log_object.log_info(
                        title=_("Batch validation successful. %s %s were not validated.") % (len(unvalid_pickings), picking_name),
                        message=_("Unvalidated %s (%s/%s): %s") % (picking_name, len(unvalid_pickings), len(pickings), details)
                    )
                    if batch_name == 'ValidateSupplierOrdersUpdated':
                        self.synchronize_receptions()
                    if batch_name == 'ValidateCustomerOrdersUpdated':
                        self.synchronize_deliveries()
                    if batch_name == 'ValidateCustomerReturnsUpdated':
                        self.synchronize_returns()
                else:
                    log_object.log_error(title=_("Batch validation failed with status code %s.") % (result))
        else:
            log_object.log_warning(
                title=_("Batch validation skipped. %s %s were not validated, exceeding the limit of %s.") % (len(unvalid_pickings), picking_name, round(unvalid_pickings_limit)),
                message=_("Unvalidated %s (%s/%s): %s") % (picking_name, len(unvalid_pickings), len(pickings), details)
            )

    ############# Cron methods ################

    def cron_synchronize_pickings(self):
        for connection in self.search([('is_used_for_cron', '=', True)]):
            connection.synchronize_pickings(
                sync_deliveries=True,
                sync_receptions=True,
                sync_returns=True,
            )   
    

    def cron_synchronize_products(self):
        for conn in self.search([('is_used_for_cron', '=', True)]):
            conn.synchronize_products(synchronize_stock=True)