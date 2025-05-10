#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funções utilitárias para o sistema
"""

import logging
import time
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

from aiogram import types
from aiogram.utils.exceptions import ChatNotFound, BotBlocked, UserDeactivated

logger = logging.getLogger(__name__)

def generate_random_string(length: int = 10) -> str:
    """Gera uma string aleatória"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def format_price(price: Union[int, float, str]) -> str:
    """Formata um preço para exibição"""
    try:
        if isinstance(price, str):
            price = float(price)
        return f"R$ {price:.2f}".replace('.', ',')
    except (ValueError, TypeError):
        logger.error(f"Erro ao formatar preço: {price}")
        return "R$ 0,00"

def parse_price(price_str: str) -> float:
    """Converte uma string de preço para float"""
    try:
        # Remove símbolo R$ e espaços
        price_str = price_str.replace('R$', '').replace(' ', '')
        # Substitui vírgula por ponto
        price_str = price_str.replace(',', '.')
        return float(price_str)
    except (ValueError, TypeError):
        logger.error(f"Erro ao converter preço: {price_str}")
        return 0.0

def get_period_timestamps(period: str) -> Tuple[float, float]:
    """Obtém timestamps de início e fim para um período"""
    now = datetime.now()
    end_time = time.time()
    
    if period == "7_days":
        start_time = (now - timedelta(days=7)).timestamp()
    elif period == "15_days":
        start_time = (now - timedelta(days=15)).timestamp()
    elif period == "30_days":
        start_time = (now - timedelta(days=30)).timestamp()
    elif period == "3_months":
        start_time = (now - timedelta(days=90)).timestamp()
    elif period == "6_months":
        start_time = (now - timedelta(days=180)).timestamp()
    elif period == "1_year":
        start_time = (now - timedelta(days=365)).timestamp()
    else:  # all_time
        start_time = 0
    
    return start_time, end_time

def calculate_plan_expiry_date(plan_type: str) -> Optional[datetime]:
    """Calcula a data de expiração com base no tipo de plano"""
    now = datetime.now()
    
    if plan_type == "1_day":
        return now + timedelta(days=1)
    elif plan_type == "7_days":
        return now + timedelta(days=7)
    elif plan_type == "15_days":
        return now + timedelta(days=15)
    elif plan_type == "30_days":
        return now + timedelta(days=30)
    elif plan_type == "3_months":
        return now + timedelta(days=90)
    elif plan_type == "6_months":
        return now + timedelta(days=180)
    elif plan_type == "1_year":
        return now + timedelta(days=365)
    elif plan_type == "lifetime":
        return None  # Sem expiração
    
    return None

async def is_user_in_channel(bot, user_id: int, channel_id: Union[int, str]) -> bool:
    """Verifica se o usuário está em um canal/grupo"""
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status not in ['left', 'kicked']
    except (ChatNotFound, BotBlocked, UserDeactivated):
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar membro {user_id} em {channel_id}: {e}", exc_info=True)
        return False

def create_bot_info_text(bot_data: Dict) -> str:
    """Cria texto com informações do bot"""
    username = bot_data.get("username", "")
    bot_id = bot_data.get("id", "")
    status = "🟢 Ativo" if bot_data.get("status") == "active" else "🔴 Desativado"
    
    return f"🤖 Seus Bots\n@{username}\n🆔: {bot_id}\n📊: Status ({status})"

def build_menu_keyboard(user_id: int, bot_data: Dict) -> types.InlineKeyboardMarkup:
    """Cria teclado para menu de gerenciamento de bots"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    username = bot_data.get("username", "")
    bot_id = bot_data.get("id", "")
    is_active = bot_data.get("status") == "active"
    
    # Botão para acessar o bot
    keyboard.add(types.InlineKeyboardButton(
        text=f"🟢 @{username}",
        url=f"https://t.me/{username}"
    ))
    
    # Botão para pausar/ativar bot
    status_text = "🔴 Pausar Bot" if is_active else "🟢 Ativar Bot"
    status_action = f"pause_bot:{bot_id}" if is_active else f"resume_bot:{bot_id}"
    keyboard.add(types.InlineKeyboardButton(
        text=status_text,
        callback_data=status_action
    ))
    
    # Botão para atualizar token
    keyboard.add(types.InlineKeyboardButton(
        text="🔄 Atualizar Token",
        callback_data=f"update_token:{bot_id}"
    ))
    
    # Botão para excluir bot
    keyboard.add(types.InlineKeyboardButton(
        text="🗑 Excluir Bot",
        callback_data=f"delete_bot:{bot_id}"
    ))
    
    # Botão para voltar
    keyboard.add(types.InlineKeyboardButton(
        text="🔙 Voltar",
        callback_data="back_to_bots"
    ))
    
    return keyboard

def build_bots_list_keyboard(bots: List[Dict]) -> types.InlineKeyboardMarkup:
    """Cria teclado com lista de bots do usuário"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for bot in bots:
        username = bot.get("username", "")
        bot_id = bot.get("id", "")
        status = "🟢" if bot.get("status") == "active" else "🔴"
        
        keyboard.add(types.InlineKeyboardButton(
            text=f"{status} @{username}",
            callback_data=f"select_bot:{bot_id}"
        ))
    
    # Adicionar botão para criar novo bot
    keyboard.add(types.InlineKeyboardButton(
        text="➕ Adicionar novo bot",
        callback_data="create_bot"
    ))
    
    # Botão para voltar
    keyboard.add(types.InlineKeyboardButton(
        text="🔙 Voltar",
        callback_data="back_to_menu"
    ))
    
    return keyboard

def build_channel_info_text(chat_config: Dict) -> str:
    """Cria texto com informações do canal/grupo configurado"""
    if not chat_config:
        return "👥 Configuração do Chat VIP\nStatus: ❌ Não configurado"
    
    chat_id = chat_config.get("chat_id", "")
    chat_title = chat_config.get("chat_title", "")
    
    text = (
        "👥 Configuração do Chat VIP\n"
        f"Status: ✅ Configurado\n"
        f"Chat: {chat_title}\n"
        f"ID: {chat_id}"
    )
    
    return text

def get_plan_duration_text(plan_type: str) -> str:
    """Retorna texto da duração do plano"""
    if plan_type == "1_day":
        return "1 Dia"
    elif plan_type == "7_days":
        return "7 Dias"
    elif plan_type == "15_days":
        return "15 Dias"
    elif plan_type == "30_days":
        return "30 Dias"
    elif plan_type == "3_months":
        return "3 Meses"
    elif plan_type == "6_months":
        return "6 Meses"
    elif plan_type == "1_year":
        return "1 Ano"
    elif plan_type == "lifetime":
        return "Vitalício"
    
    return "Desconhecido"