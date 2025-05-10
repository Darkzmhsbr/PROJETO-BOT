#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integração com a API PushinPay para envio de PIX (cashOut).
"""

import requests
import logging
from typing import Dict, Optional
from config.settings import PUSHINPAY_TOKEN, PUSHINPAY_API_URL

# Configuração de logs
logger = logging.getLogger(__name__)

class PushinPayCashOut:
    """
    Classe para gerenciar a integração com a API PushinPay para envios de PIX.
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

    def send_pix(self, value: int, pix_key: str, pix_key_type: str, webhook_url: Optional[str] = None) -> Dict:
        """
        Realiza o envio de um PIX.

        Args:
            value (int): Valor da transferência em centavos (ex.: R$1,00 = 100).
            pix_key (str): Chave PIX do destinatário.
            pix_key_type (str): Tipo da chave PIX (ex.: evp, national_registration, phone, email).
            webhook_url (Optional[str]): URL para webhook de notificações.

        Returns:
            Dict: Dados da transferência realizada.
        """
        url = f"{self.base_url}/api/pix/cashOut"
        payload = {
            "value": value,
            "pix_key": pix_key,
            "pix_key_type": pix_key_type
        }
        if webhook_url:
            payload["webhook_url"] = webhook_url

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info(f"PIX enviado com sucesso: {response.json()}")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Erro ao enviar PIX: {e}")
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

    def validate_pix_key(self, pix_key: str, pix_key_type: str) -> bool:
        """
        Valida a chave PIX e o tipo.

        Args:
            pix_key (str): Chave PIX a ser validada.
            pix_key_type (str): Tipo da chave PIX (evp, national_registration, phone, email).

        Returns:
            bool: True se a chave for válida, False caso contrário.
        """
        valid_key_types = ["evp", "national_registration", "phone", "email"]
        if pix_key_type not in valid_key_types:
            logger.error(f"Tipo de chave PIX inválido: {pix_key_type}")
            return False

        if not pix_key:
            logger.error("Chave PIX não pode ser vazia.")
            return False

        # Adicionar aqui validações adicionais específicas para cada tipo de chave (opcional)
        return True