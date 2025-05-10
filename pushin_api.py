import os
import requests

class PushinPayAPI:
    def __init__(self):
        self.api_key = os.getenv("PUSHIN_PAY_TOKEN")
        self.base_url = "https://api.pushinpay.com.br"  # Corrigido!

        if not self.api_key:
            raise ValueError("A chave da API (PUSHIN_PAY_TOKEN) não foi encontrada no arquivo .env")

    def create_pix_qrcode(self, amount_in_cents: int) -> dict:
        """Cria um QR Code PIX via API da PushinPay"""
        url = f"{self.base_url}/api/pix/cashIn"  # <--- corrigido aqui!
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "value": amount_in_cents,
            # "webhook_url": "https://seu-site.com"  # Opcional se você quiser webhook
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def check_transaction_status(self, transaction_id: str) -> dict:
        """Consulta o status de uma transação PIX"""
        url = f"{self.base_url}/api/transactions/{transaction_id}"  # <--- corrigido aqui também
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
