#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funções de order bump para os bots dos usuários
"""

import logging
import uuid
from typing import Dict, Any, Optional

from core.database import Database

logger = logging.getLogger(__name__)

async def get_order_bump_config(user_bot) -> Optional[Dict[str, Any]]:
    """
    Obtém a configuração de order bump para o bot do usuário
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        Optional[Dict]: Configuração de order bump ou None se não estiver configurada
    """
    try:
        db = Database()
        
        query = """
            SELECT id, text, price, link, active 
            FROM order_bump_configs 
            WHERE user_id = %s
        """
        
        result = await db.fetch_one(query, (user_bot.user_id,))
        
        if not result:
            return None
        
        return {
            "id": str(result["id"]),
            "text": result["text"],
            "price": float(result["price"]),
            "link": result["link"],
            "active": bool(result["active"])
        }
    except Exception as e:
        logger.error(f"Erro ao obter configuração de order bump: {e}", exc_info=True)
        return None

async def save_order_bump_config(user_bot, config: Dict[str, Any]) -> bool:
    """
    Salva a configuração de order bump para o bot do usuário
    
    Args:
        user_bot: Instância do UserBot
        config: Configuração de order bump
            - text: Texto do botão
            - price: Preço da oferta
            - link: Link da oferta
            - active: Se a oferta está ativa (opcional, padrão True)
        
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    try:
        db = Database()
        
        # Verifica se já existe configuração
        query = """
            SELECT id FROM order_bump_configs 
            WHERE user_id = %s
        """
        
        existing = await db.fetch_one(query, (user_bot.user_id,))
        
        # Prepara os dados
        text = config.get("text", "")
        price = config.get("price", 0)
        link = config.get("link", "")
        active = config.get("active", True)
        
        if existing:
            # Atualiza a configuração existente
            query = """
                UPDATE order_bump_configs 
                SET text = %s, price = %s, link = %s, 
                    active = %s, updated_at = NOW() 
                WHERE user_id = %s
            """
            
            await db.execute(
                query, 
                (
                    text,
                    price,
                    link,
                    active,
                    user_bot.user_id
                )
            )
        else:
            # Insere nova configuração
            query = """
                INSERT INTO order_bump_configs (
                    id, user_id, text, price, 
                    link, active, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            
            config_id = str(uuid.uuid4())
            
            await db.execute(
                query, 
                (
                    config_id,
                    user_bot.user_id,
                    text,
                    price,
                    link,
                    active
                )
            )
        
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configuração de order bump: {e}", exc_info=True)
        return False

async def toggle_order_bump(user_bot) -> bool:
    """
    Alterna o status de ativação do order bump
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    try:
        db = Database()
        
        # Verifica o estado atual
        query = """
            SELECT active FROM order_bump_configs 
            WHERE user_id = %s
        """
        
        result = await db.fetch_one(query, (user_bot.user_id,))
        
        if not result:
            return False
        
        # Inverte o estado
        new_state = not bool(result["active"])
        
        # Atualiza o estado
        query = """
            UPDATE order_bump_configs 
            SET active = %s, updated_at = NOW() 
            WHERE user_id = %s
        """
        
        await db.execute(query, (new_state, user_bot.user_id))
        
        return True
    except Exception as e:
        logger.error(f"Erro ao alternar status do order bump: {e}", exc_info=True)
        return False

async def is_order_bump_active(user_bot) -> bool:
    """
    Verifica se o order bump está ativo
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        bool: True se o order bump estiver ativo, False caso contrário
    """
    try:
        config = await get_order_bump_config(user_bot)
        return config is not None and config.get("active", False)
    except Exception as e:
        logger.error(f"Erro ao verificar status do order bump: {e}", exc_info=True)
        return False

async def get_order_bump_button(user_bot) -> Optional[Dict[str, Any]]:
    """
    Obtém os dados para criar o botão de order bump
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        Optional[Dict]: Dados do botão ou None se o order bump não estiver ativo
    """
    try:
        config = await get_order_bump_config(user_bot)
        
        if not config or not config.get("active", False):
            return None
        
        return {
            "text": config.get("text", "Order Bump"),
            "price": float(config.get("price", 0)),
            "callback_data": "order_bump"
        }
    except Exception as e:
        logger.error(f"Erro ao obter dados do botão de order bump: {e}", exc_info=True)
        return None