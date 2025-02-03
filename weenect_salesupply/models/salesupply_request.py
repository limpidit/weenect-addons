
import requests
from requests.exceptions import RequestException
from werkzeug.urls import url_join
from datetime import datetime

from odoo import _
from odoo.exceptions import ValidationError

class SalesupplyRequest:
    
    def __init__(self, connection):
        self.base_url = connection.api_host
        self.api_username = connection.api_username
        self.api_password = connection.api_password
        self.session = requests.Session()
        
    def _send_request(self, url, method='GET', data=None, json=None):
        url = url_join(self.base_url, url)
        auth = (self.api_username, self.api_password)
        try:
            res = self.session.request(
                method=method, 
                url=url, 
                json=json, 
                data=data,
                auth=auth, 
                timeout=15
            )
        except RequestException as exception:
            raise ValidationError(_('Something went wrong, please try again later!!'))
        finally:
            if res.status_code == 200:
                res = res.json()
            else:
                res = {'error_message': res.json()}
        return res
    
    def _get_api_user_info(self):
        url = "/v1/Me"
        response = self._send_request(url)
        return response
    
    def _get_shops(self):
        url = "/v1/Shops"
        response = self._send_request(url)
        return response
            
    def _get_shop_details(self, shop_id):
        url = f"/v1/Shops/{shop_id}"
        response = self._send_request(url)
        return response
            
    def _get_shop_group_products(self, shop_group_id):
        url = f"/v1/ShopGroup/{shop_group_id}/Products"
        response = self._send_request(url)
        return response
    
    def _get_warehouse_stock(self, warehouse_id):
        url = f"/v1/Warehouses/{warehouse_id}/Stock"
        response = self._send_request(url)
        return response
    
    def _post_product(self, product_data):
        url = self.base_url + "/v1/Products"
        auth = (self.api_username, self.api_password)
        headers = {
            "Content-type": "application/json"
        }
        response = requests.post(url, auth=auth, headers=headers, data=product_data)
        if response.status_code == 200:
            return response.json()
        else:
            raise ValidationError(response.text)
        
    def _get_receptions(self, shop_owner_id, warehouse_id, date_from=None):
        url = f"/v1/ShopOwners/{shop_owner_id}/PurchaseOrders?warehouseId={warehouse_id}"
        if date_from and isinstance(date_from, datetime):
            url += f"&fromDateChanged={date_from.strftime('%Y-%m-%d')}"
        response = self._send_request(url)
        return response
    
    def _get_reception_details(self, reception_id):
        url = f"/v1/PurchaseOrders/{reception_id}"
        response = self._send_request(url)
        return response
    
    def _get_shipments(self, warehouse_id, date_from=False):
        url = f"/v1/Warehouses/{warehouse_id}/Shipments"
        if date_from and isinstance(date_from, datetime):
            url += f"?fromDateChanged={date_from.strftime('%Y-%m-%d')}"
        response = self._send_request(url)
        return response
    
    def _get_shipment_details(self, shipment_id):
        url=f"/v1/Shipments/{shipment_id}"
        response = self._send_request(url)
        return response
    
    def _get_shipments(self, shop_id, warehouses, date_from=None):
        detailled_shipments = {warehouse_id: [] for warehouse_id in warehouses.mapped('id_salesupply')}
        url = f"v1/Shops/{shop_id}/Shipments"
        if date_from and isinstance(date_from, datetime):
            url += f"&fromDateChanged={date_from.strftime('%Y-%m-%d')}"
        response = self._send_request(url)
        for shipment in response:
            if isinstance(shipment, dict):
                shipment_response = self._send_request(f"v1/Shipments/{shipment['Id']}")
                warehouse_id = shipment_response.get('WarehouseId')
                if warehouse_id in detailled_shipments:
                    detailled_shipments[warehouse_id].append(shipment_response)
        return detailled_shipments
    
    def _get_returns(self, shop_id, warehouses, date_from=None):
        detailled_returns = {warehouse_id: [] for warehouse_id in warehouses.mapped('id_salesupply')}
        url = f"v1/Shops/{shop_id}/Returns"
        if date_from and isinstance(date_from, datetime):
            url += f"&fromDateChanged={date_from.strftime('%Y-%m-%d')}"
        response = self._send_request(url)
        for return_picking in response:
            if isinstance(return_picking, dict):
                return_response = self._send_request(f"v1/Returns/{return_picking['Id']}")
                warehouse_id = return_response.get('WarehouseId')
                if warehouse_id in detailled_returns:
                    detailled_returns[warehouse_id].append(return_response)
        return detailled_returns