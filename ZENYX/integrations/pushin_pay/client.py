# integrations/pushin_pay/client.py
import requests
import logging
import os
from typing import Dict, Any, Optional

class PushinPayClient:
    """Cliente para a API da Pushin Pay"""
    
    def __init__(self, token: str, base_url: str):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Realiza uma requisição para a API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na requisição para Pushin Pay: {e}")
            if hasattr(e, 'response') and e.response:
                logging.error(f"Resposta: {e.response.text}")
            raise
    
    def create_pix_qrcode(self, value: int, webhook_url: Optional[str] = None) -> Dict:
        """Cria um QRCode PIX para pagamento"""
        data = {"value": value}
        
        if webhook_url:
            data["webhook_url"] = webhook_url
            
        return self._request("POST", "/pix/cashIn", data)
    
    def check_transaction_status(self, transaction_id: str) -> Dict:
        """Consulta o status de uma transação"""
        return self._request("GET", f"/transactions/{transaction_id}")
    
    def make_pix_transfer(self, value: int, pix_key_type: str, pix_key: str, webhook_url: Optional[str] = None) -> Dict:
        """Realiza uma transferência PIX"""
        data = {
            "value": value,
            "pix_key_type": pix_key_type,
            "pix_key": pix_key
        }
        
        if webhook_url:
            data["webhook_url"] = webhook_url
            
        return self._request("POST", "/pix/cashOut", data)
    
    def check_transfer_status(self, transfer_id: str) -> Dict:
        """Consulta o status de uma transferência"""
        return self._request("GET", f"/transfers/{transfer_id}")
    
    def refund_transaction(self, transaction_id: str) -> Dict:
        """Realiza o estorno de uma transação"""
        return self._request("POST", f"/transactions/{transaction_id}/refund")