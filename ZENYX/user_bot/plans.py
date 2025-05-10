#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gerenciamento de planos para os bots dos usuários
"""

import logging
import uuid
from typing import List, Dict, Any, Optional

from core.database import Database
from core.utils import format_price

logger = logging.getLogger(__name__)

async def get_plans(user_bot) -> List[Dict[str, Any]]:
    """
    Obtém todos os planos configurados para o bot do usuário
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        List[Dict]: Lista de planos
    """
    try:
        db = Database()
        
        query = """
            SELECT id, name, price, duration, active 
            FROM plans 
            WHERE user_id = %s
            ORDER BY price ASC
        """
        
        plans = await db.fetch_all(query, (user_bot.user_id,))
        
        # Formata os planos para o formato esperado pelo sistema
        formatted_plans = []
        for plan in plans:
            plan_data = {
                "id": str(plan["id"]),
                "name": plan["name"],
                "price": float(plan["price"]),
                "duration": plan["duration"],
                "active": bool(plan["active"])
            }
            
            formatted_plans.append(plan_data)
            
        return formatted_plans
    except Exception as e:
        logger.error(f"Erro ao obter planos: {e}", exc_info=True)
        return []

async def get_plan(user_bot, plan_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtém um plano específico pelo ID
    
    Args:
        user_bot: Instância do UserBot
        plan_id: ID do plano
        
    Returns:
        Optional[Dict]: Dados do plano ou None se não encontrado
    """
    try:
        db = Database()
        
        query = """
            SELECT id, name, price, duration, active 
            FROM plans 
            WHERE id = %s AND user_id = %s
        """
        
        plan = await db.fetch_one(query, (plan_id, user_bot.user_id))
        
        if not plan:
            return None
        
        return {
            "id": str(plan["id"]),
            "name": plan["name"],
            "price": float(plan["price"]),
            "duration": plan["duration"],
            "active": bool(plan["active"])
        }
    except Exception as e:
        logger.error(f"Erro ao obter plano {plan_id}: {e}", exc_info=True)
        return None

async def save_plan(user_bot, plan_data: Dict[str, Any]) -> bool:
    """
    Salva um plano no banco de dados
    
    Args:
        user_bot: Instância do UserBot
        plan_data: Dados do plano a ser salvo
            - name: Nome do plano
            - price: Preço do plano
            - duration: Duração do plano
            - active: Se o plano está ativo (opcional, padrão True)
        
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    try:
        db = Database()
        
        # Prepara os dados do plano
        name = plan_data.get("name", "")
        price = plan_data.get("price", 0)
        duration = plan_data.get("duration", "30_days")
        active = plan_data.get("active", True)
        
        # Insere o plano no banco de dados
        query = """
            INSERT INTO plans (
                id, user_id, name, price, duration, active, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        
        plan_id = str(uuid.uuid4())
        
        await db.execute(
            query, 
            (
                plan_id,
                user_bot.user_id,
                name,
                price,
                duration,
                active
            )
        )
        
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar plano: {e}", exc_info=True)
        return False

async def update_plan(user_bot, plan_id: str, plan_data: Dict[str, Any]) -> bool:
    """
    Atualiza um plano existente no banco de dados
    
    Args:
        user_bot: Instância do UserBot
        plan_id: ID do plano a ser atualizado
        plan_data: Novos dados do plano
            - name: Nome do plano (opcional)
            - price: Preço do plano (opcional)
            - duration: Duração do plano (opcional)
            - active: Se o plano está ativo (opcional)
        
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    try:
        db = Database()
        
        # Obtém o plano atual
        query = """
            SELECT name, price, duration, active 
            FROM plans 
            WHERE id = %s AND user_id = %s
        """
        
        current_plan = await db.fetch_one(query, (plan_id, user_bot.user_id))
        
        if not current_plan:
            return False
        
        # Prepara os dados atualizados
        name = plan_data.get("name", current_plan["name"])
        price = plan_data.get("price", float(current_plan["price"]))
        duration = plan_data.get("duration", current_plan["duration"])
        active = plan_data.get("active", bool(current_plan["active"]))
        
        # Atualiza o plano no banco de dados
        query = """
            UPDATE plans 
            SET name = %s, price = %s, duration = %s, active = %s, updated_at = NOW() 
            WHERE id = %s AND user_id = %s
        """
        
        await db.execute(
            query, 
            (
                name,
                price,
                duration,
                active,
                plan_id,
                user_bot.user_id
            )
        )
        
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar plano {plan_id}: {e}", exc_info=True)
        return False

async def delete_plan(user_bot, plan_id: str) -> bool:
    """
    Remove um plano do banco de dados
    
    Args:
        user_bot: Instância do UserBot
        plan_id: ID do plano a ser removido
        
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    try:
        db = Database()
        
        # Remove o plano
        query = "DELETE FROM plans WHERE id = %s AND user_id = %s"
        await db.execute(query, (plan_id, user_bot.user_id))
        
        return True
    except Exception as e:
        logger.error(f"Erro ao excluir plano {plan_id}: {e}", exc_info=True)
        return False

async def toggle_plan(user_bot, plan_id: str) -> bool:
    """
    Alterna o status ativo/inativo de um plano
    
    Args:
        user_bot: Instância do UserBot
        plan_id: ID do plano
        
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    try:
        db = Database()
        
        # Obtém o estado atual do plano
        query = "SELECT active FROM plans WHERE id = %s AND user_id = %s"
        result = await db.fetch_one(query, (plan_id, user_bot.user_id))
        
        if not result:
            return False
        
        # Inverte o estado
        new_state = not bool(result["active"])
        
        # Atualiza o estado
        query = "UPDATE plans SET active = %s, updated_at = NOW() WHERE id = %s AND user_id = %s"
        await db.execute(query, (new_state, plan_id, user_bot.user_id))
        
        return True
    except Exception as e:
        logger.error(f"Erro ao alternar status do plano {plan_id}: {e}", exc_info=True)
        return False

def format_plan_info(plan: Dict[str, Any]) -> str:
    """
    Formata informações do plano para exibição
    
    Args:
        plan: Dados do plano
        
    Returns:
        str: Texto formatado
    """
    try:
        # Formata o preço
        formatted_price = format_price(plan.get("price", 0))
        
        # Formata a duração
        duration = plan.get("duration", "30_days")
        duration_text = "Vitalício"
        
        if duration == "1_day":
            duration_text = "1 Dia"
        elif duration == "7_days":
            duration_text = "7 Dias"
        elif duration == "15_days":
            duration_text = "15 Dias"
        elif duration == "30_days":
            duration_text = "30 Dias"
        elif duration == "3_months":
            duration_text = "3 Meses"
        elif duration == "6_months":
            duration_text = "6 Meses"
        elif duration == "1_year":
            duration_text = "1 Ano"
        
        # Status do plano
        status = "✅ Ativo" if plan.get("active", True) else "❌ Inativo"
        
        # Retorna o texto formatado
        return (
            f"🏷 *{plan.get('name', 'Plano')}*\n"
            f"💰 Preço: {formatted_price}\n"
            f"⏱ Duração: {duration_text}\n"
            f"📊 Status: {status}"
        )
    except Exception as e:
        logger.error(f"Erro ao formatar informações do plano: {e}", exc_info=True)
        return "Erro ao formatar plano"