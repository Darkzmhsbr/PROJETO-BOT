#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gerenciamento de banco de dados Redis
"""

import json
import logging
import aioredis
import time
from typing import Dict, List, Optional, Any, Union

from config.settings import get_redis_url
from config.constants import BotStatus, PaymentStatus

logger = logging.getLogger(__name__)

class Database:
    """Classe para gerenciar operações no banco de dados Redis"""
    
    def __init__(self):
        """Inicializa a conexão com o Redis"""
        self.redis = None
        self.connected = False
    
    async def connect(self):
        """Estabelece conexão com o Redis"""
        if not self.connected:
            try:
                self.redis = await aioredis.from_url(
                    get_redis_url(),
                    encoding="utf-8",
                    decode_responses=True
                )
                self.connected = True
                logger.info("Conexão com o Redis estabelecida")
            except Exception as e:
                logger.error(f"Erro ao conectar ao Redis: {e}", exc_info=True)
                raise
    
    async def ensure_connected(self):
        """Garante que a conexão com o Redis está estabelecida"""
        if not self.connected:
            await self.connect()
    
    async def close(self):
        """Fecha a conexão com o Redis"""
        if self.connected and self.redis:
            await self.redis.close()
            self.connected = False
            logger.info("Conexão com o Redis fechada")
    
    # Métodos para gerenciar usuários
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Obtém informações de um usuário"""
        await self.ensure_connected()
        user_data = await self.redis.get(f"user:{user_id}")
        return json.loads(user_data) if user_data else None
    
    async def save_user(self, user_id: int, user_data: Dict) -> bool:
        """Salva informações de um usuário"""
        await self.ensure_connected()
        user_data["updated_at"] = time.time()
        if "created_at" not in user_data:
            user_data["created_at"] = time.time()
        
        try:
            await self.redis.set(f"user:{user_id}", json.dumps(user_data))
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar usuário {user_id}: {e}", exc_info=True)
            return False
    
    async def update_user(self, user_id: int, updates: Dict) -> bool:
        """Atualiza informações de um usuário"""
        user_data = await self.get_user(user_id)
        if not user_data:
            return False
        
        user_data.update(updates)
        return await self.save_user(user_id, user_data)
    
    async def delete_user(self, user_id: int) -> bool:
        """Remove um usuário do banco de dados"""
        await self.ensure_connected()
        try:
            await self.redis.delete(f"user:{user_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar usuário {user_id}: {e}", exc_info=True)
            return False
    
    async def is_user_in_channel(self, user_id: int) -> bool:
        """Verifica se o usuário está no canal oficial"""
        user_data = await self.get_user(user_id)
        return user_data.get("in_channel", False) if user_data else False
    
    async def set_user_in_channel(self, user_id: int, in_channel: bool) -> bool:
        """Define o status de participação do usuário no canal"""
        return await self.update_user(user_id, {"in_channel": in_channel})
    
    # Métodos para gerenciar bots de usuários
    
    async def save_user_bot(self, user_id: int, bot_data: Dict) -> str:
        """Salva um novo bot de usuário"""
        await self.ensure_connected()
        
        # Gera ID do bot
        bot_count = await self.redis.incr("bot_id_counter")
        bot_id = str(bot_count).zfill(2)  # ID formatado com zeros à esquerda (01, 02, etc)
        
        # Prepara dados do bot
        bot_data.update({
            "id": bot_id,
            "user_id": user_id,
            "created_at": time.time(),
            "updated_at": time.time(),
            "status": BotStatus.ACTIVE
        })
        
        # Salva dados do bot
        await self.redis.set(f"bot:{bot_id}", json.dumps(bot_data))
        
        # Adiciona à lista de bots do usuário
        await self.redis.sadd(f"user:{user_id}:bots", bot_id)
        
        # Adiciona à lista de todos os bots
        await self.redis.sadd("all_bots", bot_id)
        
        return bot_id
    
    async def get_user_bot(self, bot_id: str) -> Optional[Dict]:
        """Obtém informações de um bot de usuário"""
        await self.ensure_connected()
        bot_data = await self.redis.get(f"bot:{bot_id}")
        return json.loads(bot_data) if bot_data else None
    
    async def get_user_bot_by_token(self, token: str) -> Optional[Dict]:
        """Obtém um bot pelo token"""
        await self.ensure_connected()
        all_bots = await self.redis.smembers("all_bots")
        
        for bot_id in all_bots:
            bot_data = await self.get_user_bot(bot_id)
            if bot_data and bot_data.get("token") == token:
                return bot_data
        
        return None
    
    async def get_user_bot_by_username(self, username: str) -> Optional[Dict]:
        """Obtém um bot pelo username"""
        await self.ensure_connected()
        all_bots = await self.redis.smembers("all_bots")
        
        for bot_id in all_bots:
            bot_data = await self.get_user_bot(bot_id)
            if bot_data and bot_data.get("username") == username:
                return bot_data
        
        return None
    
    async def get_user_bots(self, user_id: int) -> List[Dict]:
        """Obtém todos os bots de um usuário"""
        await self.ensure_connected()
        bot_ids = await self.redis.smembers(f"user:{user_id}:bots")
        
        bots = []
        for bot_id in bot_ids:
            bot_data = await self.get_user_bot(bot_id)
            if bot_data:
                bots.append(bot_data)
        
        return bots
    
    async def get_all_user_bots(self) -> List[Dict]:
        """Obtém todos os bots do sistema"""
        await self.ensure_connected()
        bot_ids = await self.redis.smembers("all_bots")
        
        bots = []
        for bot_id in bot_ids:
            bot_data = await self.get_user_bot(bot_id)
            if bot_data:
                bots.append(bot_data)
        
        return bots
    
    async def get_new_user_bots(self, since_timestamp: float) -> List[Dict]:
        """Obtém bots criados após determinado timestamp"""
        all_bots = await self.get_all_user_bots()
        return [bot for bot in all_bots if bot.get("created_at", 0) > since_timestamp]
    
    async def get_stopped_user_bots(self) -> List[Dict]:
        """Obtém bots que estão marcados para parar"""
        all_bots = await self.get_all_user_bots()
        return [bot for bot in all_bots if bot.get("status") == BotStatus.INACTIVE or bot.get("status") == BotStatus.DELETED]
    
    async def update_user_bot(self, bot_id: str, updates: Dict) -> bool:
        """Atualiza informações de um bot"""
        bot_data = await self.get_user_bot(bot_id)
        if not bot_data:
            return False
        
        bot_data.update(updates)
        bot_data["updated_at"] = time.time()
        
        await self.ensure_connected()
        await self.redis.set(f"bot:{bot_id}", json.dumps(bot_data))
        return True
    
    async def update_user_bot_status(self, bot_id: str, is_active: bool) -> bool:
        """Atualiza o status de um bot"""
        status = BotStatus.ACTIVE if is_active else BotStatus.INACTIVE
        return await self.update_user_bot(bot_id, {"status": status})
    
    async def delete_user_bot(self, bot_id: str) -> bool:
        """Remove um bot do sistema"""
        await self.ensure_connected()
        
        bot_data = await self.get_user_bot(bot_id)
        if not bot_data:
            return False
        
        user_id = bot_data.get("user_id")
        
        try:
            # Remove das listas
            await self.redis.srem(f"user:{user_id}:bots", bot_id)
            await self.redis.srem("all_bots", bot_id)
            
            # Remove dados do bot
            await self.redis.delete(f"bot:{bot_id}")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar bot {bot_id}: {e}", exc_info=True)
            return False
    
    # Métodos para gerenciar mensagens dos bots
    
    async def save_bot_message(self, bot_id: str, message_data: Dict) -> str:
        """Salva uma mensagem de um bot"""
        await self.ensure_connected()
        
        # Gera ID da mensagem
        message_count = await self.redis.incr(f"bot:{bot_id}:message_counter")
        message_id = str(message_count)
        
        # Prepara dados da mensagem
        message_data.update({
            "id": message_id,
            "bot_id": bot_id,
            "created_at": time.time(),
            "updated_at": time.time()
        })
        
        # Salva dados da mensagem
        await self.redis.set(f"bot:{bot_id}:message:{message_id}", json.dumps(message_data))
        
        # Adiciona à lista de mensagens do bot
        await self.redis.sadd(f"bot:{bot_id}:messages", message_id)
        
        return message_id
    
    async def get_bot_message(self, bot_id: str, message_id: str) -> Optional[Dict]:
        """Obtém uma mensagem de um bot"""
        await self.ensure_connected()
        message_data = await self.redis.get(f"bot:{bot_id}:message:{message_id}")
        return json.loads(message_data) if message_data else None
    
    async def get_bot_messages(self, bot_id: str) -> List[Dict]:
        """Obtém todas as mensagens de um bot"""
        await self.ensure_connected()
        message_ids = await self.redis.smembers(f"bot:{bot_id}:messages")
        
        messages = []
        for message_id in message_ids:
            message_data = await self.get_bot_message(bot_id, message_id)
            if message_data:
                messages.append(message_data)
        
        # Ordena por ordem de criação
        messages.sort(key=lambda x: int(x.get("id", 0)))
        
        return messages
    
    async def update_bot_message(self, bot_id: str, message_id: str, updates: Dict) -> bool:
        """Atualiza informações de uma mensagem"""
        message_data = await self.get_bot_message(bot_id, message_id)
        if not message_data:
            return False
        
        message_data.update(updates)
        message_data["updated_at"] = time.time()
        
        await self.ensure_connected()
        await self.redis.set(f"bot:{bot_id}:message:{message_id}", json.dumps(message_data))
        return True
    
    async def delete_bot_message(self, bot_id: str, message_id: str) -> bool:
        """Remove uma mensagem do bot"""
        await self.ensure_connected()
        
        try:
            # Remove da lista de mensagens
            await self.redis.srem(f"bot:{bot_id}:messages", message_id)
            
            # Remove dados da mensagem
            await self.redis.delete(f"bot:{bot_id}:message:{message_id}")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem {message_id} do bot {bot_id}: {e}", exc_info=True)
            return False
    
    async def delete_all_bot_messages(self, bot_id: str) -> bool:
        """Remove todas as mensagens de um bot"""
        await self.ensure_connected()
        
        message_ids = await self.redis.smembers(f"bot:{bot_id}:messages")
        
        try:
            for message_id in message_ids:
                await self.redis.delete(f"bot:{bot_id}:message:{message_id}")
            
            await self.redis.delete(f"bot:{bot_id}:messages")
            await self.redis.delete(f"bot:{bot_id}:message_counter")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar todas as mensagens do bot {bot_id}: {e}", exc_info=True)
            return False
    
    # Métodos para gerenciar planos
    
    async def save_bot_plan(self, bot_id: str, plan_data: Dict) -> str:
        """Salva um plano de um bot"""
        await self.ensure_connected()
        
        # Gera ID do plano
        plan_count = await self.redis.incr(f"bot:{bot_id}:plan_counter")
        plan_id = str(plan_count)
        
        # Prepara dados do plano
        plan_data.update({
            "id": plan_id,
            "bot_id": bot_id,
            "created_at": time.time(),
            "updated_at": time.time()
        })
        
        # Salva dados do plano
        await self.redis.set(f"bot:{bot_id}:plan:{plan_id}", json.dumps(plan_data))
        
        # Adiciona à lista de planos do bot
        await self.redis.sadd(f"bot:{bot_id}:plans", plan_id)
        
        return plan_id
    
    async def get_bot_plan(self, bot_id: str, plan_id: str) -> Optional[Dict]:
        """Obtém um plano de um bot"""
        await self.ensure_connected()
        plan_data = await self.redis.get(f"bot:{bot_id}:plan:{plan_id}")
        return json.loads(plan_data) if plan_data else None
    
    async def get_bot_plans(self, bot_id: str) -> List[Dict]:
        """Obtém todos os planos de um bot"""
        await self.ensure_connected()
        plan_ids = await self.redis.smembers(f"bot:{bot_id}:plans")
        
        plans = []
        for plan_id in plan_ids:
            plan_data = await self.get_bot_plan(bot_id, plan_id)
            if plan_data:
                plans.append(plan_data)
        
        return plans
    
    async def update_bot_plan(self, bot_id: str, plan_id: str, updates: Dict) -> bool:
        """Atualiza informações de um plano"""
        plan_data = await self.get_bot_plan(bot_id, plan_id)
        if not plan_data:
            return False
        
        plan_data.update(updates)
        plan_data["updated_at"] = time.time()
        
        await self.ensure_connected()
        await self.redis.set(f"bot:{bot_id}:plan:{plan_id}", json.dumps(plan_data))
        return True
    
    async def delete_bot_plan(self, bot_id: str, plan_id: str) -> bool:
        """Remove um plano do bot"""
        await self.ensure_connected()
        
        try:
            # Remove da lista de planos
            await self.redis.srem(f"bot:{bot_id}:plans", plan_id)
            
            # Remove dados do plano
            await self.redis.delete(f"bot:{bot_id}:plan:{plan_id}")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar plano {plan_id} do bot {bot_id}: {e}", exc_info=True)
            return False
    
    # Métodos para gerenciar pagamentos
    
    async def save_payment(self, payment_data: Dict) -> str:
        """Salva um novo pagamento"""
        await self.ensure_connected()
        
        payment_id = payment_data.get("id", str(int(time.time())))
        
        # Prepara dados do pagamento
        if "created_at" not in payment_data:
            payment_data["created_at"] = time.time()
        payment_data["updated_at"] = time.time()
        
        # Salva dados do pagamento
        await self.redis.set(f"payment:{payment_id}", json.dumps(payment_data))
        
        # Adiciona à lista de pagamentos do usuário
        user_id = payment_data.get("user_id")
        if user_id:
            await self.redis.sadd(f"user:{user_id}:payments", payment_id)
        
        # Adiciona à lista de pagamentos do bot
        bot_id = payment_data.get("bot_id")
        if bot_id:
            await self.redis.sadd(f"bot:{bot_id}:payments", payment_id)
        
        return payment_id
    
    async def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Obtém informações de um pagamento"""
        await self.ensure_connected()
        payment_data = await self.redis.get(f"payment:{payment_id}")
        return json.loads(payment_data) if payment_data else None
    
    async def update_payment(self, payment_id: str, updates: Dict) -> bool:
        """Atualiza informações de um pagamento"""
        payment_data = await self.get_payment(payment_id)
        if not payment_data:
            return False
        
        payment_data.update(updates)
        payment_data["updated_at"] = time.time()
        
        await self.ensure_connected()
        await self.redis.set(f"payment:{payment_id}", json.dumps(payment_data))
        return True
    
    async def get_user_payments(self, user_id: int) -> List[Dict]:
        """Obtém todos os pagamentos de um usuário"""
        await self.ensure_connected()
        payment_ids = await self.redis.smembers(f"user:{user_id}:payments")
        
        payments = []
        for payment_id in payment_ids:
            payment_data = await self.get_payment(payment_id)
            if payment_data:
                payments.append(payment_data)
        
        return payments
    
    async def get_bot_payments(self, bot_id: str) -> List[Dict]:
        """Obtém todos os pagamentos de um bot"""
        await self.ensure_connected()
        payment_ids = await self.redis.smembers(f"bot:{bot_id}:payments")
        
        payments = []
        for payment_id in payment_ids:
            payment_data = await self.get_payment(payment_id)
            if payment_data:
                payments.append(payment_data)
        
        return payments
    
    async def get_bot_payments_by_period(self, bot_id: str, start_time: float, end_time: float) -> List[Dict]:
        """Obtém pagamentos de um bot em um período específico"""
        all_payments = await self.get_bot_payments(bot_id)
        
        return [
            payment for payment in all_payments
            if start_time <= payment.get("created_at", 0) <= end_time
            and payment.get("status") == PaymentStatus.PAID
        ]
    
    # Métodos para gerenciar configurações de remarketing, upsell e order bump
    
    async def save_bot_feature_config(self, bot_id: str, feature: str, config_data: Dict) -> bool:
        """Salva configuração de uma funcionalidade do bot"""
        await self.ensure_connected()
        
        config_data["updated_at"] = time.time()
        if "created_at" not in config_data:
            config_data["created_at"] = time.time()
        
        try:
            await self.redis.set(f"bot:{bot_id}:{feature}_config", json.dumps(config_data))
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configuração de {feature} para bot {bot_id}: {e}", exc_info=True)
            return False
    
    async def get_bot_feature_config(self, bot_id: str, feature: str) -> Optional[Dict]:
        """Obtém configuração de uma funcionalidade do bot"""
        await self.ensure_connected()
        config_data = await self.redis.get(f"bot:{bot_id}:{feature}_config")
        return json.loads(config_data) if config_data else None
    
    async def delete_bot_feature_config(self, bot_id: str, feature: str) -> bool:
        """Remove configuração de uma funcionalidade do bot"""
        await self.ensure_connected()
        try:
            await self.redis.delete(f"bot:{bot_id}:{feature}_config")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar configuração de {feature} para bot {bot_id}: {e}", exc_info=True)
            return False
