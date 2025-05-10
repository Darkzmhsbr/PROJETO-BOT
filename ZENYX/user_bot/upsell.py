#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funções de upsell para os bots dos usuários
"""

import logging
import uuid
import asyncio
from typing import Dict, Any, Optional

from aiogram import types
from core.database import Database
from core.bot_manager import get_bot_instance
from user_bot.payment import create_payment

logger = logging.getLogger(__name__)

async def get_upsell_config(user_bot) -> Optional[Dict[str, Any]]:
    """
    Obtém a configuração de upsell para o bot do usuário
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        Optional[Dict]: Configuração de upsell ou None se não estiver configurada
    """
    try:
        db = Database()
        
        query = """
            SELECT id, text, button_text, price, link, active 
            FROM upsell_configs 
            WHERE user_id = %s
        """
        
        result = await db.fetch_one(query, (user_bot.user_id,))
        
        if not result:
            return None
        
        return {
            "id": str(result["id"]),
            "text": result["text"],
            "button_text": result["button_text"],
            "price": float(result["price"]),
            "link": result["link"],
            "active": bool(result["active"])
        }
    except Exception as e:
        logger.error(f"Erro ao obter configuração de upsell: {e}", exc_info=True)
        return None

async def save_upsell_config(user_bot, config: Dict[str, Any]) -> bool:
    """
    Salva a configuração de upsell para o bot do usuário
    
    Args:
        user_bot: Instância do UserBot
        config: Configuração de upsell
            - text: Texto da oferta
            - button_text: Texto do botão
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
            SELECT id FROM upsell_configs 
            WHERE user_id = %s
        """
        
        existing = await db.fetch_one(query, (user_bot.user_id,))
        
        # Prepara os dados
        text = config.get("text", "")
        button_text = config.get("button_text", "")
        price = config.get("price", 0)
        link = config.get("link", "")
        active = config.get("active", True)
        
        if existing:
            # Atualiza a configuração existente
            query = """
                UPDATE upsell_configs 
                SET text = %s, button_text = %s, price = %s, link = %s, 
                    active = %s, updated_at = NOW() 
                WHERE user_id = %s
            """
            
            await db.execute(
                query, 
                (
                    text,
                    button_text,
                    price,
                    link,
                    active,
                    user_bot.user_id
                )
            )
        else:
            # Insere nova configuração
            query = """
                INSERT INTO upsell_configs (
                    id, user_id, text, button_text, price, 
                    link, active, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            config_id = str(uuid.uuid4())
            
            await db.execute(
                query, 
                (
                    config_id,
                    user_bot.user_id,
                    text,
                    button_text,
                    price,
                    link,
                    active
                )
            )
        
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configuração de upsell: {e}", exc_info=True)
        return False

async def toggle_upsell(user_bot) -> bool:
    """
    Alterna o status de ativação do upsell
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    try:
        db = Database()
        
        # Verifica o estado atual
        query = """
            SELECT active FROM upsell_configs 
            WHERE user_id = %s
        """
        
        result = await db.fetch_one(query, (user_bot.user_id,))
        
        if not result:
            return False
        
        # Inverte o estado
        new_state = not bool(result["active"])
        
        # Atualiza o estado
        query = """
            UPDATE upsell_configs 
            SET active = %s, updated_at = NOW() 
            WHERE user_id = %s
        """
        
        await db.execute(query, (new_state, user_bot.user_id))
        
        return True
    except Exception as e:
        logger.error(f"Erro ao alternar status do upsell: {e}", exc_info=True)
        return False

async def send_upsell_offer(user_bot, user_id: int, payment_id: str) -> None:
    """
    Envia oferta de upsell após um período de espera
    
    Args:
        user_bot: Instância do UserBot
        user_id: ID do usuário que efetuou pagamento
        payment_id: ID do pagamento associado
    """
    try:
        # Espera 3 minutos antes de enviar a oferta
        await asyncio.sleep(180)  # 3 minutos = 180 segundos
        
        # Verifica se o upsell está configurado e ativo
        upsell_config = await get_upsell_config(user_bot)
        
        if not upsell_config or not upsell_config.get("active", False):
            logger.info(f"Upsell não configurado ou inativo para o bot {user_bot.user_id}")
            return
        
        # Obtém instância do bot
        bot = await get_bot_instance(user_bot.user_id)
        
        if not bot:
            logger.error(f"Não foi possível obter instância do bot {user_bot.user_id}")
            return
        
        # Prepara dados para criar pagamento
        payment_data = {
            "user_id": user_id,
            "amount": upsell_config["price"],
            "payment_type": "upsell",
            "original_payment_id": payment_id,
            "upsell_link": upsell_config["link"]
        }
        
        # Cria pagamento para o upsell
        payment_result = await create_payment(user_bot, payment_data)
        
        if not payment_result.get("success", False):
            logger.error(f"Erro ao criar pagamento de upsell: {payment_result.get('error', 'Erro desconhecido')}")
            return
        
        # Obtém URL de pagamento
        payment_url = payment_result.get("payment_url", "")
        
        if not payment_url:
            logger.error("URL de pagamento não gerada")
            return
        
        # Cria teclado com o botão de pagamento
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                text=upsell_config["button_text"],
                url=payment_url
            )
        )
        
        # Envia mensagem de upsell
        await bot.send_message(
            chat_id=user_id,
            text=upsell_config["text"],
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(f"Oferta de upsell enviada para o usuário {user_id}")
    except Exception as e:
        logger.error(f"Erro ao enviar oferta de upsell: {e}", exc_info=True)

async def process_upsell_payment(user_id: int, bot_owner_id: int, upsell_link: str) -> None:
    """
    Processa um pagamento de upsell
    
    Args:
        user_id: ID do usuário que pagou
        bot_owner_id: ID do dono do bot
        upsell_link: Link do upsell
    """
    try:
        # Obtém instância do bot
        from core.bot_manager import get_bot_instance
        bot = await get_bot_instance(bot_owner_id)
        
        if not bot:
            logger.error(f"Não foi possível obter instância do bot {bot_owner_id}")
            return
        
        # Envia link ao usuário
        await bot.send_message(
            chat_id=user_id,
            text=f"🎉 *Parabéns! Seu pagamento da oferta adicional foi aprovado!*\n\n"
                 f"Clique no botão abaixo para acessar o conteúdo exclusivo:",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(
                    text="🔑 ACESSAR CONTEÚDO ADICIONAL",
                    url=upsell_link
                )
            ),
            parse_mode="Markdown"
        )
        
        logger.info(f"Acesso ao upsell processado para usuário {user_id} no bot {bot_owner_id}")
    except Exception as e:
        logger.error(f"Erro ao processar pagamento de upsell: {e}", exc_info=True)