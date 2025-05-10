#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Métricas e estatísticas para os bots dos usuários
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from core.database import Database
from core.utils import get_period_timestamps

logger = logging.getLogger(__name__)

async def get_sales_metrics(user_bot, period: str = "30_days") -> Dict[str, Any]:
    """
    Obtém métricas de vendas para o bot do usuário
    
    Args:
        user_bot: Instância do UserBot
        period: Período para as métricas
            - 7_days: Últimos 7 dias
            - 15_days: Últimos 15 dias
            - 30_days: Últimos 30 dias
            - 3_months: Últimos 3 meses
            - 6_months: Últimos 6 meses
            - 1_year: Último ano
            - all_time: Todo o período
            
    Returns:
        Dict: Métricas de vendas
            - total_sales: Valor total de vendas
            - sales_count: Número de vendas
            - commission: Valor de comissão (20%)
            - total_users: Número total de usuários
            - paying_users: Número de usuários pagantes
    """
    try:
        # Obtém timestamps do período
        start_timestamp, _ = get_period_timestamps(period)
        
        db = Database()
        
        # Vendas para o período
        if period == "all_time":
            query = """
                SELECT 
                    COUNT(*) as sales_count, 
                    COALESCE(SUM(amount), 0) as total_amount 
                FROM payments 
                WHERE bot_owner_id = %s AND status = 'paid'
            """
            
            sales = await db.fetch_one(query, (user_bot.user_id,))
        else:
            start_date = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            query = """
                SELECT 
                    COUNT(*) as sales_count, 
                    COALESCE(SUM(amount), 0) as total_amount 
                FROM payments 
                WHERE bot_owner_id = %s AND status = 'paid' 
                AND paid_at >= %s
            """
            
            sales = await db.fetch_one(query, (user_bot.user_id, start_date))
        
        # Dados de usuários
        query = """
            SELECT COUNT(DISTINCT user_id) as total_users 
            FROM user_bot_interactions 
            WHERE bot_id = %s
        """
        
        users = await db.fetch_one(query, (user_bot.user_id,))
        
        # Usuários pagantes
        query = """
            SELECT COUNT(DISTINCT user_id) as paying_users 
            FROM user_accesses 
            WHERE bot_owner_id = %s
        """
        
        paying = await db.fetch_one(query, (user_bot.user_id,))
        
        # Formata os resultados
        sales_count = sales["sales_count"] if sales else 0
        total_sales = float(sales["total_amount"]) if sales and sales["total_amount"] else 0
        commission = total_sales * 0.2  # 20% de comissão
        
        total_users = users["total_users"] if users else 0
        paying_users = paying["paying_users"] if paying else 0
        
        return {
            "total_sales": total_sales,
            "sales_count": sales_count,
            "commission": commission,
            "total_users": total_users,
            "paying_users": paying_users
        }
    except Exception as e:
        logger.error(f"Erro ao obter métricas de vendas: {e}", exc_info=True)
        return {
            "total_sales": 0,
            "sales_count": 0,
            "commission": 0,
            "total_users": 0,
            "paying_users": 0
        }

async def get_user_metrics(user_bot) -> Dict[str, Any]:
    """
    Obtém métricas de usuários para o bot
    
    Args:
        user_bot: Instância do UserBot
        
    Returns:
        Dict: Métricas de usuários
            - total: Total de usuários
            - active_24h: Usuários ativos nas últimas 24h
            - active_7d: Usuários ativos nos últimos 7 dias
            - new_24h: Novos usuários nas últimas 24h
            - new_7d: Novos usuários nos últimos 7 dias
    """
    try:
        db = Database()
        
        # Timestamp para 24h atrás
        timestamp_24h = int(time.time()) - (24 * 60 * 60)
        date_24h = datetime.fromtimestamp(timestamp_24h).strftime('%Y-%m-%d %H:%M:%S')
        
        # Timestamp para 7 dias atrás
        timestamp_7d = int(time.time()) - (7 * 24 * 60 * 60)
        date_7d = datetime.fromtimestamp(timestamp_7d).strftime('%Y-%m-%d %H:%M:%S')
        
        # Total de usuários
        query = """
            SELECT COUNT(DISTINCT user_id) as total 
            FROM user_bot_interactions 
            WHERE bot_id = %s
        """
        
        total = await db.fetch_one(query, (user_bot.user_id,))
        
        # Usuários ativos nas últimas 24h
        query = """
            SELECT COUNT(DISTINCT user_id) as active_24h 
            FROM user_bot_interactions 
            WHERE bot_id = %s 
            AND last_interaction_at >= %s
        """
        
        active_24h = await db.fetch_one(query, (user_bot.user_id, date_24h))
        
        # Usuários ativos nos últimos 7 dias
        query = """
            SELECT COUNT(DISTINCT user_id) as active_7d 
            FROM user_bot_interactions 
            WHERE bot_id = %s 
            AND last_interaction_at >= %s
        """
        
        active_7d = await db.fetch_one(query, (user_bot.user_id, date_7d))
        
        # Novos usuários nas últimas 24h
        query = """
            SELECT COUNT(DISTINCT user_id) as new_24h 
            FROM user_bot_interactions 
            WHERE bot_id = %s 
            AND first_interaction_at >= %s
        """
        
        new_24h = await db.fetch_one(query, (user_bot.user_id, date_24h))
        
        # Novos usuários nos últimos 7 dias
        query = """
            SELECT COUNT(DISTINCT user_id) as new_7d 
            FROM user_bot_interactions 
            WHERE bot_id = %s 
            AND first_interaction_at >= %s
        """
        
        new_7d = await db.fetch_one(query, (user_bot.user_id, date_7d))
        
        return {
            "total": total["total"] if total else 0,
            "active_24h": active_24h["active_24h"] if active_24h else 0,
            "active_7d": active_7d["active_7d"] if active_7d else 0,
            "new_24h": new_24h["new_24h"] if new_24h else 0,
            "new_7d": new_7d["new_7d"] if new_7d else 0
        }
    except Exception as e:
        logger.error(f"Erro ao obter métricas de usuários: {e}", exc_info=True)
        return {
            "total": 0,
            "active_24h": 0,
            "active_7d": 0,
            "new_24h": 0,
            "new_7d": 0
        }

async def get_sales_chart_data(user_bot, period: str = "30_days") -> Dict[str, Any]:
    """
    Obtém dados para gráfico de vendas
    
    Args:
        user_bot: Instância do UserBot
        period: Período para os dados
            - 7_days: Últimos 7 dias
            - 15_days: Últimos 15 dias
            - 30_days: Últimos 30 dias
            - 3_months: Últimos 3 meses
            - 6_months: Últimos 6 meses
            - 1_year: Último ano
            
    Returns:
        Dict: Dados para o gráfico
            - labels: Rótulos para o eixo X
            - data: Valores de vendas para cada rótulo
    """
    try:
        db = Database()
        
        # Determina o formato dos rótulos e a granularidade dos dados
        if period in ["7_days", "15_days"]:
            # Diário
            format_str = "%d/%m"
            group_by = "DATE(paid_at)"
            
            if period == "7_days":
                days = 7
            else:
                days = 15
        elif period == "30_days":
            # Diário
            format_str = "%d/%m"
            group_by = "DATE(paid_at)"
            days = 30
        elif period == "3_months":
            # Semanal
            format_str = "Semana %U"
            group_by = "YEARWEEK(paid_at)"
            days = 90
        elif period == "6_months":
            # Semanal
            format_str = "Semana %U"
            group_by = "YEARWEEK(paid_at)"
            days = 180
        elif period == "1_year":
            # Mensal
            format_str = "%m/%Y"
            group_by = "DATE_FORMAT(paid_at, '%Y-%m')"
            days = 365
        else:
            # Padrão: diário
            format_str = "%d/%m"
            group_by = "DATE(paid_at)"
            days = 30
        
        # Data de início
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Consulta para obter dados agrupados
        query = f"""
            SELECT 
                {group_by} as time_group, 
                DATE_FORMAT(paid_at, %s) as formatted_date, 
                COALESCE(SUM(amount), 0) as total_amount, 
                COUNT(*) as count
            FROM payments 
            WHERE bot_owner_id = %s AND status = 'paid' 
            AND paid_at >= %s
            GROUP BY time_group
            ORDER BY time_group ASC
        """
        
        results = await db.fetch_all(query, (format_str, user_bot.user_id, start_date))
        
        # Prepara dados para o gráfico
        labels = []
        data = []
        
        for row in results:
            labels.append(row["formatted_date"])
            data.append(float(row["total_amount"]))
        
        return {
            "labels": labels,
            "data": data
        }
    except Exception as e:
        logger.error(f"Erro ao obter dados para gráfico de vendas: {e}", exc_info=True)
        return {
            "labels": [],
            "data": []
        }