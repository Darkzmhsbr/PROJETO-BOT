#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modelo de Pagamentos - Representa pagamentos realizados para os bots.
"""

from datetime import datetime
from typing import Optional

class Payment:
    """
    Representa um pagamento feito por um usuário para um plano de bot.
    """

    def __init__(
        self,
        user_id: str,
        plan_id: str,
        amount: float,
        method: str,
        status: str = "pending",
        transaction_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        """
        Inicializa um novo pagamento.

        Args:
            user_id (str): ID do usuário que realizou o pagamento.
            plan_id (str): ID do plano associado ao pagamento.
            amount (float): Valor do pagamento.
            method (str): Método de pagamento (ex.: "credit_card", "pix", "boleto").
            status (str): Status do pagamento (ex.: "pending", "completed", "failed").
            transaction_id (Optional[str]): ID da transação (fornecido pelo gateway de pagamento).
            created_at (Optional[datetime]): Data de criação do pagamento.
        """
        self.user_id = user_id
        self.plan_id = plan_id
        self.amount = amount
        self.method = method
        self.status = status
        self.transaction_id = transaction_id
        self.created_at = created_at or datetime.now()

    def update_status(self, new_status: str):
        """
        Atualiza o status do pagamento.

        Args:
            new_status (str): Novo status do pagamento.
        """
        self.status = new_status

    def __repr__(self):
        return f"<Payment user_id={self.user_id}, amount={self.amount}, status={self.status}>"