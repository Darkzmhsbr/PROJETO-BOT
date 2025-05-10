#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integração com a API PushinPay para operações de PIX (cashIn).
"""

import requests
import logging
from typing import Dict, Optional
from config.settings import PUSHINPAY_TOKEN, PUSHINPAY_API_URL

# Configuração de logs
logger = logging.getLogger(__name__)

class PushinPayIntegration:
    """
    Classe para gerenciar a integração com a API PushinPay.
    """

    def __init__(self):
        """
        Inicializa a integração com a API PushinPay.
        """
        if not PUSHINPAY_TOKEN or not PUSHINPAY_API_URL:
            raise ValueError("PUSHINPAY_TOKEN e PUSHINPAY_API_URL precisam estar configurados.")
        self.headers = {
            "Authorization": f"Bearer {PUSHINPAY_TOKEN}",
            "Content-Type": "application/json",
        }
        self.base_url = PUSHINPAY_API_URL

    def create_qrcode(self, value: int, webhook_url: Optional[str] = None) -> Dict:
        """
        Cria um QR Code PIX para pagamento.

        Args:
            value (int): Valor do pagamento em centavos (ex.: R$1,00 = 100).
            webhook_url (Optional[str]): URL para webhook de notificações.

        Returns:
            Dict: Dados do QR Code gerado.
        """
        url = f"{self.base_url}/api/pix/cashIn"
        payload = {"value": value}
        if webhook_url:
            payload["webhook_url"] = webhook_url

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info(f"QR Code PIX criado com sucesso: {response.json()}")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Erro ao criar QR Code PIX: {e}")
            raise

    def get_transaction_status(self, transaction_id: str) -> Dict:
        """
        Consulta o status de uma transação PIX.

        Args:
            transaction_id (str): ID da transação.

        Returns:
            Dict: Dados do status da transação.
        """
        url = f"{self.base_url}/api/transactions/{transaction_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            logger.info(f"Status da transação consultado com sucesso: {response.json()}")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Erro ao consultar status da transação: {e}")
            raise