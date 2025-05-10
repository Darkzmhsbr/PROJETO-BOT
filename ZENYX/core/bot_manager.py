#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gerenciamento de bots de usuários.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from aiogram import Bot
from aiogram.utils.exceptions import TelegramAPIError

from core.database import Database
from config.constants import BotStatus

logger = logging.getLogger(__name__)

class UserBot:
    """Classe que representa um bot de usuário"""
    
    def __init__(self, bot: Bot, bot_data: Dict, db: Database):
        """Inicializa um bot de usuário"""
        self.bot = bot
        self.bot_data = bot_data
        self.db = db
        self.id = bot_data.get("id")
        self.user_id = bot_data.get("user_id")
        self.token = bot_data.get("token")
        self.username = bot_data.get("username")
    
    async def get_username(self) -> str:
        """Obtém o username do bot"""
        if not self.username:
            try:
                me = await self.bot.get_me()
                self.username = me.username
                # Atualiza no banco de dados
                await self.db.update_user_bot(self.id, {"username": self.username})
            except Exception as e:
                logger.error(f"Erro ao obter username do bot {self.id}: {e}", exc_info=True)
        
        return self.username
    
    async def get_messages(self) -> List[Dict]:
        """Obtém mensagens configuradas do bot"""
        return await self.db.get_bot_messages(self.id)
    
    async def save_message(self, message_data: Dict) -> str:
        """Salva uma mensagem"""
        return await self.db.save_bot_message(self.id, message_data)
    
    async def update_message(self, message_id: str, updates: Dict) -> bool:
        """Atualiza uma mensagem"""
        return await self.db.update_bot_message(self.id, message_id, updates)
    
    async def delete_message(self, message_id: str) -> bool:
        """Remove uma mensagem"""
        return await self.db.delete_bot_message(self.id, message_id)
    
    async def delete_all_messages(self) -> bool:
        """Remove todas as mensagens"""
        return await self.db.delete_all_bot_messages(self.id)
    
    async def get_plans(self) -> List[Dict]:
        """Obtém planos configurados do bot"""
        return await self.db.get_bot_plans(self.id)
    
    async def save_plan(self, plan_data: Dict) -> str:
        """Salva um plano"""
        return await self.db.save_bot_plan(self.id, plan_data)
    
    async def update_plan(self, plan_id: str, updates: Dict) -> bool:
        """Atualiza um plano"""
        return await self.db.update_bot_plan(self.id, plan_id, updates)
    
    async def delete_plan(self, plan_id: str) -> bool:
        """Remove um plano"""
        return await self.db.delete_bot_plan(self.id, plan_id)
    
    async def get_upsell_config(self) -> Optional[Dict]:
        """Obtém configuração de upsell"""
        return await self.db.get_bot_feature_config(self.id, "upsell")
    
    async def save_upsell_config(self, config_data: Dict) -> bool:
        """Salva configuração de upsell"""
        return await self.db.save_bot_feature_config(self.id, "upsell", config_data)
    
    async def get_order_bump_config(self) -> Optional[Dict]:
        """Obtém configuração de order bump"""
        return await self.db.get_bot_feature_config(self.id, "order_bump")
    
    async def save_order_bump_config(self, config_data: Dict) -> bool:
        """Salva configuração de order bump"""
        return await self.db.save_bot_feature_config(self.id, "order_bump", config_data)
    
    async def get_support_config(self) -> Optional[Dict]:
        """Obtém configuração de suporte"""
        return await self.db.get_bot_feature_config(self.id, "support")
    
    async def save_support_config(self, config_data: Dict) -> bool:
        """Salva configuração de suporte"""
        return await self.db.save_bot_feature_config(self.id, "support", config_data)
    
    async def get_chat_config(self) -> Optional[Dict]:
        """Obtém configuração de chat VIP"""
        return await self.db.get_bot_feature_config(self.id, "chat")
    
    async def save_chat_config(self, config_data: Dict) -> bool:
        """Salva configuração de chat VIP"""
        return await self.db.save_bot_feature_config(self.id, "chat", config_data)
    
    async def get_payments(self) -> List[Dict]:
        """Obtém pagamentos do bot"""
        return await self.db.get_bot_payments(self.id)
    
    async def get_payments_by_period(self, start_time: float, end_time: float) -> List[Dict]:
        """Obtém pagamentos em um período específico"""
        return await self.db.get_bot_payments_by_period(self.id, start_time, end_time)
    
    async def get_pushinpay_token(self) -> Optional[str]:
        """Obtém token da PushinPay configurado"""
        pushinpay_config = await self.db.get_bot_feature_config(self.id, "pushinpay")
        return pushinpay_config.get("token") if pushinpay_config else None
    
    async def save_pushinpay_token(self, token: str) -> bool:
        """Salva token da PushinPay"""
        return await self.db.save_bot_feature_config(self.id, "pushinpay", {"token": token})


class BotManager:
    """Classe para gerenciar bots de usuários"""
    
    def __init__(self, main_bot: Bot, db: Database):
        """Inicializa o gerenciador de bots"""
        self.main_bot = main_bot
        self.db = db
    
    async def create_user_bot(self, user_id: int, token: str) -> Optional[Dict]:
        """Cria um novo bot para o usuário"""
        try:
            # Verifica se o token é válido
            temp_bot = Bot(token=token)
            me = await temp_bot.get_me()
            await temp_bot.close()
            
            # Salva informações do bot
            bot_data = {
                "token": token,
                "username": me.username,
                "first_name": me.first_name,
                "user_id": user_id,
                "status": BotStatus.ACTIVE
            }
            
            bot_id = await self.db.save_user_bot(user_id, bot_data)
            
            if bot_id:
                bot_data["id"] = bot_id
                logger.info(f"Bot criado: {bot_id} - @{me.username} para usuário {user_id}")
                return bot_data
            
            return None
        except TelegramAPIError as e:
            logger.error(f"Erro ao validar token do bot: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Erro ao criar bot para usuário {user_id}: {e}", exc_info=True)
            return None
    
    async def get_user_bots(self, user_id: int) -> List[Dict]:
        """Obtém todos os bots de um usuário"""
        return await self.db.get_user_bots(user_id)
    
    async def get_user_bot(self, bot_id: str) -> Optional[Dict]:
        """Obtém informações de um bot específico"""
        return await self.db.get_user_bot(bot_id)
    
    async def pause_user_bot(self, bot_id: str) -> bool:
        """Pausa um bot de usuário"""
        return await self.db.update_user_bot_status(bot_id, False)
    
    async def resume_user_bot(self, bot_id: str) -> bool:
        """Retoma um bot de usuário"""
        return await self.db.update_user_bot_status(bot_id, True)
    
    async def delete_user_bot(self, bot_id: str) -> bool:
        """Remove um bot de usuário"""
        # Primeiro desativa o bot
        await self.db.update_user_bot(bot_id, {"status": BotStatus.DELETED})
        
        # Aguarda um pouco para garantir que o bot será parado pelo sistema
        await asyncio.sleep(2)
        
        # Remove do banco de dados
        return await self.db.delete_user_bot(bot_id)
    
    async def update_user_bot_token(self, bot_id: str, new_token: str) -> bool:
        """Atualiza o token de um bot de usuário"""
        try:
            # Verifica se o token é válido
            temp_bot = Bot(token=new_token)
            me = await temp_bot.get_me()
            await temp_bot.close()
            
            # Atualiza informações do bot
            updates = {
                "token": new_token,
                "username": me.username,
                "first_name": me.first_name,
                "status": BotStatus.ACTIVE
            }
            
            # Pausa o bot atual
            await self.db.update_user_bot_status(bot_id, False)
            
            # Atualiza com o novo token
            result = await self.db.update_user_bot(bot_id, updates)
            
            logger.info(f"Token atualizado para bot {bot_id}")
            return result
        except TelegramAPIError as e:
            logger.error(f"Erro ao validar novo token do bot: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Erro ao atualizar token do bot {bot_id}: {e}", exc_info=True)
            return False