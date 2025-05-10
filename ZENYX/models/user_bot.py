# models/user_bot.py
from typing import Dict, Any, List, Optional
import json
import time

class UserBot:
    """Modelo para bots de usuários"""
    
    def __init__(self, bot_id: str, user_id: int, token: str, username: str):
        self.bot_id = bot_id
        self.user_id = user_id
        self.token = token
        self.username = username
        self.active = True
        self.created_at = int(time.time())
        self.channel_id = None
        self.pushin_token = None
        self.welcome_messages = []
        self.plans = []
        self.upsell = None
        self.order_bump = None
        self.support_username = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Converte o bot para dicionário"""
        return {
            "bot_id": self.bot_id,
            "user_id": self.user_id,
            "token": self.token,
            "username": self.username,
            "active": self.active,
            "created_at": self.created_at,
            "channel_id": self.channel_id,
            "pushin_token": self.pushin_token,
            "welcome_messages": self.welcome_messages,
            "plans": self.plans,
            "upsell": self.upsell,
            "order_bump": self.order_bump,
            "support_username": self.support_username
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserBot':
        """Cria um bot a partir de um dicionário"""
        bot = cls(
            bot_id=data["bot_id"],
            user_id=data["user_id"],
            token=data["token"],
            username=data["username"]
        )
        bot.active = data.get("active", True)
        bot.created_at = data.get("created_at", int(time.time()))
        bot.channel_id = data.get("channel_id")
        bot.pushin_token = data.get("pushin_token")
        bot.welcome_messages = data.get("welcome_messages", [])
        bot.plans = data.get("plans", [])
        bot.upsell = data.get("upsell")
        bot.order_bump = data.get("order_bump")
        bot.support_username = data.get("support_username")
        return bot
    
    @classmethod
    async def get(cls, redis_conn, bot_id: str) -> Optional['UserBot']:
        """Obtém um bot do Redis"""
        bot_data = await redis_conn.get(f"bot:{bot_id}")
        
        if not bot_data:
            return None
            
        return cls.from_dict(json.loads(bot_data))
    
    async def save(self, redis_conn) -> None:
        """Salva o bot no Redis"""
        # Salva o bot
        await redis_conn.set(f"bot:{self.bot_id}", json.dumps(self.to_dict()))
        
        # Adiciona à lista de bots do usuário
        await redis_conn.sadd(f"user:{self.user_id}:bots", self.bot_id)
        
        # Atualiza o contador de bots
        await redis_conn.incr("bot_counter", 0)
    
    @classmethod
    async def get_all(cls, redis_conn) -> List['UserBot']:
        """Obtém todos os bots do Redis"""
        bot_keys = await redis_conn.keys("bot:*")
        bots = []
        
        for key in bot_keys:
            bot_data = await redis_conn.get(key)
            
            if bot_data:
                bots.append(cls.from_dict(json.loads(bot_data)))
                
        return bots
    
    @classmethod
    async def get_by_user(cls, redis_conn, user_id: int) -> List['UserBot']:
        """Obtém todos os bots de um usuário"""
        bot_ids = await redis_conn.smembers(f"user:{user_id}:bots")
        bots = []
        
        for bot_id in bot_ids:
            bot_data = await redis_conn.get(f"bot:{bot_id}")
            
            if bot_data:
                bots.append(cls.from_dict(json.loads(bot_data)))
                
        return bots
    
    @classmethod
    async def generate_id(cls, redis_conn) -> str:
        """Gera um ID único para o bot"""
        counter = await redis_conn.incr("bot_counter")
        return f"{counter:02d}"  # Formato: 01, 02, 03, etc.