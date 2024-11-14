
import requests
from requests.exceptions import RequestException
from werkzeug.urls import url_join

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
        return res
    
    def _process_errors(self, res_body):
        response = res_body.get('Message')
        if response:
            return response
        return _("Undefined error")
    
    def _get_api_user_info(self):
        url = "/v1/Me"
        response = self._send_request(url)
        if response.status_code == 200:
            return True
        return {
            'error_message': self._process_errors(response.json())
        }
    
    def _get_shops(self):
        url = "/v1/Shops"
        response = self._send_request(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error_message': self._process_errors(response.json())
            }
            
    def _get_shop_details(self, shop_id):
        url = f"/v1/Shops/{shop_id}"
        response = self._send_request(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error_message': self._process_errors(response.json())
            }
            
    def _get_shop_group_products(self, shop_group_id):
        url = f"/v1/ShopGroup/{shop_group_id}/Products"
        response = self._send_request(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error_message': self._process_errors(response.json())
            }
    