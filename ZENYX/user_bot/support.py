#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuração de suporte para os bots dos usuários
"""

import logging
import uuid
from typing import Dict, Any, Optional

from core.database import Database

logger = logging.getLogger(__name__)

async def get_support_config(user_bot) -> Optional[Dict[str, Any]]:
    """
    Obtém a configuração de suporte para o bot do usuário
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        Optional[Dict]: Configuração de suporte ou None se não estiver configurada
    """
    try:
        db = Database()
        
        query = """
            SELECT id, username, created_at 
            FROM support_configs 
            WHERE user_id = %s
        """
        
        result = await db.fetch_one(query, (user_bot.user_id,))
        
        if not result:
            return None
        
        return {
            "id": str(result["id"]),
            "username": result["username"],
            "created_at": result["created_at"]
        }
    except Exception as e:
        logger.error(f"Erro ao obter configuração de suporte: {e}", exc_info=True)
        return None

async def save_support_config(user_bot, config: Dict[str, Any]) -> bool:
    """
    Salva a configuração de suporte para o bot do usuário
    
    Args:
        user_bot: Instância do UserBot
        config: Configuração de suporte
            - username: Nome de usuário para contato de suporte
        
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    try:
        db = Database()
        
        # Verifica se já existe configuração
        query = """
            SELECT id FROM support_configs 
            WHERE user_id = %s
        """
        
        existing = await db.fetch_one(query, (user_bot.user_id,))
        
        # Prepara os dados
        username = config.get("username", "").strip()
        
        # Remove @ se estiver presente
        if username.startswith('@'):
            username = username[1:]
        
        if existing:
            # Atualiza a configuração existente
            query = """
                UPDATE support_configs 
                SET username = %s, updated_at = NOW() 
                WHERE user_id = %s
            """
            
            await db.execute(query, (username, user_bot.user_id))
        else:
            # Insere nova configuração
            query = """
                INSERT INTO support_configs (
                    id, user_id, username, created_at
                ) VALUES (%s, %s, %s, NOW())
            """
            
            config_id = str(uuid.uuid4())
            
            await db.execute(query, (config_id, user_bot.user_id, username))
        
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configuração de suporte: {e}", exc_info=True)
        return False

async def handle_support_command(message, user_bot) -> str:
    """
    Processa o comando de suporte e retorna a mensagem
    
    Args:
        message: Mensagem do usuário
        user_bot: Instância do UserBot
        
    Returns:
        str: Mensagem de resposta formatada
    """
    try:
        # Obtém a configuração de suporte
        support_config = await get_support_config(user_bot)
        
        if support_config and "username" in support_config:
            # Formato com username configurado
            username = support_config["username"]
            
            return (
                f"📞 *Suporte*\n\n"
                f"Para obter ajuda, entre em contato com [@{username}](https://t.me/{username}).\n\n"
                f"Nosso suporte estará disponível para resolver suas dúvidas e problemas."
            )
        else:
            # Formato sem username configurado
            return (
                f"📞 *Suporte*\n\n"
                f"Não há informações de contato de suporte configuradas para este bot.\n\n"
                f"Por favor, tente entrar em contato com o administrador do bot para obter ajuda."
            )
    except Exception as e:
        logger.error(f"Erro ao processar comando de suporte: {e}", exc_info=True)
        return "❌ Ocorreu um erro ao processar sua solicitação de suporte."

async def log_support_request(user_bot, user_id: int, username: str = None) -> None:
    """
    Registra uma solicitação de suporte
    
    Args:
        user_bot: Instância do UserBot
        user_id: ID do usuário que solicitou suporte
        username: Nome de usuário que solicitou suporte (opcional)
    """
    try:
        db = Database()
        
        # Registra a solicitação
        query = """
            INSERT INTO support_requests (
                id, user_id, bot_id, username, created_at
            ) VALUES (%s, %s, %s, %s, NOW())
        """
        
        request_id = str(uuid.uuid4())
        
        await db.execute(
            query, 
            (
                request_id,
                user_id,
                user_bot.user_id,
                username
            )
        )
        
        logger.info(f"Solicitação de suporte registrada: {user_id} ({username if username else 'sem username'}) para o bot {user_bot.user_id}")
    except Exception as e:
        logger.error(f"Erro ao registrar solicitação de suporte: {e}", exc_info=True)