# models/user.py
from typing import Dict, Any, List, Optional
import json
import time

class User:
    """Modelo para usuários do sistema"""
    
    def __init__(self, user_id: int, username: Optional[str] = None, first_name: Optional[str] = None):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.is_verified = False
        self.bots = []  # Lista de IDs de bots do usuário
        self.created_at = int(time.time())
        
    def to_dict(self) -> Dict[str, Any]:
        """Converte o usuário para dicionário"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "is_verified": self.is_verified,
            "bots": self.bots,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Cria um usuário a partir de um dicionário"""
        user = cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name")
        )
        user.is_verified = data.get("is_verified", False)
        user.bots = data.get("bots", [])
        user.created_at = data.get("created_at", int(time.time()))
        return user
    
    @classmethod
    async def get(cls, redis_conn, user_id: int) -> Optional['User']:
        """Obtém um usuário do Redis"""
        user_data = await redis_conn.get(f"user:{user_id}")
        
        if not user_data:
            return None
            
        return cls.from_dict(json.loads(user_data))
    
    async def save(self, redis_conn) -> None:
        """Salva o usuário no Redis"""
        await redis_conn.set(f"user:{self.user_id}", json.dumps(self.to_dict()))
    
    @classmethod
    async def get_all(cls, redis_conn) -> List['User']:
        """Obtém todos os usuários do Redis"""
        user_keys = await redis_conn.keys("user:*")
        users = []
        
        for key in user_keys:
            user_data = await redis_conn.get(key)
            
            if user_data:
                users.append(cls.from_dict(json.loads(user_data)))
                
        return users