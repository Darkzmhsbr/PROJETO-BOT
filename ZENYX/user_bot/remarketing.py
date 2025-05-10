#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funções de remarketing para os bots dos usuários
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional

from aiogram import types
from core.database import Database
from core.bot_manager import get_bot_instance
from user_bot.payment import create_payment

logger = logging.getLogger(__name__)

async def prepare_remarketing_message(message, user_bot, message_data: Dict[str, Any]) -> None:
    """
    Prepara e envia uma prévia da mensagem de remarketing
    
    Args:
        message: Mensagem original do usuário
        user_bot: Instância do UserBot
        message_data: Dados da mensagem de remarketing
    """
    try:
        # Determina o tipo de mensagem
        msg_type = message_data.get("type", "text")
        
        # Verifica se há promoção para adicionar
        has_promotion = "promotion" in message_data
        
        # Cria teclado para promoção se necessário
        keyboard = None
        if has_promotion:
            # Cria pagamento fictício para exibir na prévia
            promotion = message_data["promotion"]
            promo_price = promotion.get("price", 0)
            
            # Cria teclado com botão de promoção
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(
                text=f"🔥 APROVEITAR OFERTA: R$ {promo_price:.2f} 🔥",
                callback_data="preview_promo"
            ))
        
        # Envia a prévia conforme o tipo de mensagem
        if msg_type == "text":
            text = message_data.get("text", "")
            
            await message.answer(
                text=text, 
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif msg_type == "photo":
            file_id = message_data.get("file_id")
            caption = message_data.get("caption", "")
            
            await message.answer_photo(
                photo=file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif msg_type == "video":
            file_id = message_data.get("file_id")
            caption = message_data.get("caption", "")
            
            await message.answer_video(
                video=file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif msg_type == "animation":
            file_id = message_data.get("file_id")
            caption = message_data.get("caption", "")
            
            await message.answer_animation(
                animation=file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif msg_type == "voice":
            file_id = message_data.get("file_id")
            caption = message_data.get("caption", "")
            
            # Envia a mensagem de voz
            await message.answer_voice(
                voice=file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif msg_type == "audio":
            file_id = message_data.get("file_id")
            caption = message_data.get("caption", "")
            
            await message.answer_audio(
                audio=file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif msg_type == "document":
            file_id = message_data.get("file_id")
            caption = message_data.get("caption", "")
            
            await message.answer_document(
                document=file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erro ao preparar mensagem de remarketing: {e}", exc_info=True)
        await message.answer("❌ Erro ao preparar mensagem de remarketing.")

async def send_remarketing_message(user_bot, message_data: Dict[str, Any], only_non_paying: bool = False) -> int:
    """
    Envia mensagem de remarketing para usuários do bot
    
    Args:
        user_bot: Instância do UserBot
        message_data: Dados da mensagem de remarketing
        only_non_paying: Se True, envia apenas para usuários não pagantes
        
    Returns:
        int: Número de mensagens enviadas
    """
    try:
        # Obtém a lista de usuários
        db = Database()
        
        if only_non_paying:
            # Apenas usuários não pagantes
            query = """
                SELECT u.user_id 
                FROM user_bot_interactions u
                LEFT JOIN user_accesses a ON u.user_id = a.user_id AND a.bot_owner_id = %s
                WHERE u.bot_id = %s 
                AND a.id IS NULL
            """
            
            users = await db.fetch_all(query, (user_bot.user_id, user_bot.user_id))
        else:
            # Todos os usuários
            query = """
                SELECT user_id 
                FROM user_bot_interactions 
                WHERE bot_id = %s
            """
            
            users = await db.fetch_all(query, (user_bot.user_id,))
        
        if not users:
            logger.info(f"Nenhum usuário encontrado para enviar remarketing do bot {user_bot.user_id}")
            return 0
        
        # Obtém instância do bot
        bot = await get_bot_instance(user_bot.user_id)
        
        if not bot:
            logger.error(f"Não foi possível obter instância do bot {user_bot.user_id}")
            return 0
        
        # Verifica se há promoção para adicionar
        has_promotion = "promotion" in message_data
        promotion_data = None
        promo_keyboard = None
        
        if has_promotion:
            promotion_data = message_data["promotion"]
            promo_price = promotion_data.get("price", 0)
            
            # Verifica se é personalizado ou baseado em plano
            is_custom = promotion_data.get("custom", False)
            
            if is_custom:
                # Promoção personalizada
                promo_text = f"🔥 APROVEITAR OFERTA: R$ {promo_price:.2f} 🔥"
            else:
                # Promoção baseada em plano
                plan_name = promotion_data.get("plan_name", "Plano")
                promo_text = f"🔥 APROVEITAR {plan_name}: R$ {promo_price:.2f} 🔥"
        
        # Contador de mensagens enviadas
        sent_count = 0
        
        # Envia para cada usuário
        for user in users:
            user_id = user["user_id"]
            
            # Cria teclado específico para o usuário se tiver promoção
            if has_promotion:
                # Cria pagamento para o usuário
                payment_data = {
                    "user_id": user_id,
                    "amount": promotion_data.get("price", 0),
                    "payment_type": "remarketing"
                }
                
                # Adiciona dados do plano, se necessário
                if not promotion_data.get("custom", False):
                    payment_data["plan_id"] = promotion_data.get("plan_id")
                    payment_data["duration"] = promotion_data.get("plan_duration")
                
                # Cria o pagamento
                payment_result = await create_payment(user_bot, payment_data)
                
                if payment_result.get("success", False):
                    # Cria teclado com link de pagamento
                    payment_url = payment_result.get("payment_url", "")
                    
                    if payment_url:
                        promo_keyboard = types.InlineKeyboardMarkup()
                        promo_keyboard.add(types.InlineKeyboardButton(
                            text=promo_text,
                            url=payment_url
                        ))
            
            try:
                # Determina o tipo de mensagem
                msg_type = message_data.get("type", "text")
                
                # Envia a mensagem conforme o tipo
                if msg_type == "text":
                    text = message_data.get("text", "")
                    
                    await bot.send_message(
                        chat_id=user_id,
                        text=text, 
                        reply_markup=promo_keyboard,
                        parse_mode="HTML"
                    )
                elif msg_type == "photo":
                    file_id = message_data.get("file_id")
                    caption = message_data.get("caption", "")
                    
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=file_id,
                        caption=caption,
                        reply_markup=promo_keyboard,
                        parse_mode="HTML"
                    )
                elif msg_type == "video":
                    file_id = message_data.get("file_id")
                    caption = message_data.get("caption", "")
                    
                    await bot.send_video(
                        chat_id=user_id,
                        video=file_id,
                        caption=caption,
                        reply_markup=promo_keyboard,
                        parse_mode="HTML"
                    )
                elif msg_type == "animation":
                    file_id = message_data.get("file_id")
                    caption = message_data.get("caption", "")
                    
                    await bot.send_animation(
                        chat_id=user_id,
                        animation=file_id,
                        caption=caption,
                        reply_markup=promo_keyboard,
                        parse_mode="HTML"
                    )
                elif msg_type == "voice":
                    file_id = message_data.get("file_id")
                    caption = message_data.get("caption", "")
                    
                    await bot.send_voice(
                        chat_id=user_id,
                        voice=file_id,
                        caption=caption,
                        reply_markup=promo_keyboard,
                        parse_mode="HTML"
                    )
                elif msg_type == "audio":
                    file_id = message_data.get("file_id")
                    caption = message_data.get("caption", "")
                    
                    await bot.send_audio(
                        chat_id=user_id,
                        audio=file_id,
                        caption=caption,
                        reply_markup=promo_keyboard,
                        parse_mode="HTML"
                    )
                elif msg_type == "document":
                    file_id = message_data.get("file_id")
                    caption = message_data.get("caption", "")
                    
                    await bot.send_document(
                        chat_id=user_id,
                        document=file_id,
                        caption=caption,
                        reply_markup=promo_keyboard,
                        parse_mode="HTML"
                    )
                
                # Incrementa contador
                sent_count += 1
                
                # Pequeno delay para evitar flood
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Erro ao enviar remarketing para o usuário {user_id}: {e}")
                # Continua para o próximo usuário
        
        return sent_count
    except Exception as e:
        logger.error(f"Erro ao enviar mensagens de remarketing: {e}", exc_info=True)
        return 0

async def get_remarketing_targets(user_bot) -> Dict[str, int]:
    """
    Obtém o número de usuários para cada tipo de alvo de remarketing
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        Dict: Número de usuários por tipo
            - all: Todos os usuários
            - non_paying: Usuários não pagantes
    """
    try:
        db = Database()
        
        # Todos os usuários
        query = """
            SELECT COUNT(*) as count 
            FROM user_bot_interactions 
            WHERE bot_id = %s
        """
        
        all_users = await db.fetch_one(query, (user_bot.user_id,))
        all_count = all_users["count"] if all_users else 0
        
        # Usuários não pagantes
        query = """
            SELECT COUNT(DISTINCT u.user_id) as count 
            FROM user_bot_interactions u
            LEFT JOIN user_accesses a ON u.user_id = a.user_id AND a.bot_owner_id = %s
            WHERE u.bot_id = %s 
            AND a.id IS NULL
        """
        
        non_paying = await db.fetch_one(query, (user_bot.user_id, user_bot.user_id))
        non_paying_count = non_paying["count"] if non_paying else 0
        
        return {
            "all": all_count,
            "non_paying": non_paying_count
        }
    except Exception as e:
        logger.error(f"Erro ao obter alvos de remarketing: {e}", exc_info=True)
        return {
            "all": 0,
            "non_paying": 0
        }