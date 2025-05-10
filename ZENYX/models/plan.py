#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modelo de Planos - Representa os planos criados pelos usuários para seus bots.
"""

from typing import List, Optional
from datetime import datetime

class Plan:
    """
    Representa um plano de assinatura ou funcionalidade de um bot.
    """

    def __init__(
        self,
        name: str,
        price: float,
        duration_days: int,
        features: List[str],
        owner_id: str,
        created_at: Optional[datetime] = None,
        is_active: bool = True,
    ):
        """
        Inicializa um novo plano.

        Args:
            name (str): Nome do plano (ex.: "Premium").
            price (float): Valor do plano (ex.: 29.99).
            duration_days (int): Número de dias de duração do plano.
            features (List[str]): Lista de funcionalidades incluídas no plano.
            owner_id (str): ID do dono do bot associado ao plano.
            created_at (Optional[datetime]): Data de criação do plano.
            is_active (bool): Indica se o plano está ativo.
        """
        self.name = name
        self.price = price
        self.duration_days = duration_days
        self.features = features
        self.owner_id = owner_id
        self.created_at = created_at or datetime.now()
        self.is_active = is_active

    def deactivate(self):
        """Desativa o plano."""
        self.is_active = False

    def activate(self):
        """Ativa o plano."""
        self.is_active = True

    def __repr__(self):
        return f"<Plan name={self.name}, price={self.price}, active={self.is_active}>"