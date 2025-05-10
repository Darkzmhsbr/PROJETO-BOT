#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modelo de Mensagens - Representa mensagens configuradas pelos usuários para seus bots.
"""

from datetime import datetime
from typing import Optional

class Message:
    """
    Representa uma mensagem personalizada para um bot.
    """

    def __init__(
        self,
        user_id: str,
        bot_id: str,
        content: str,
        message_type: str = "text",
        created_at: Optional[datetime] = None,
        is_active: bool = True,
    ):
        """
        Inicializa uma nova mensagem.

        Args:
            user_id (str): ID do usuário que criou a mensagem.
            bot_id (str): ID do bot associado à mensagem.
            content (str): Conteúdo da mensagem.
            message_type (str): Tipo da mensagem (ex.: "text", "image", "audio").
            created_at (Optional[datetime]): Data de criação da mensagem.
            is_active (bool): Indica se a mensagem está ativa.
        """
        self.user_id = user_id
        self.bot_id = bot_id
        self.content = content
        self.message_type = message_type
        self.created_at = created_at or datetime.now()
        self.is_active = is_active

    def deactivate(self):
        """Desativa a mensagem."""
        self.is_active = False

    def activate(self):
        """Ativa a mensagem."""
        self.is_active = True

    def __repr__(self):
        return f"<Message bot_id={self.bot_id}, type={self.message_type}, active={self.is_active}>"