#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Handlers para verificação de participação no canal oficial
"""

import logging
from aiogram import Dispatcher, Bot, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from core.database import Database
from core.utils import is_user_in_channel
from config.settings import CHANNEL_ID, CHANNEL_LINK, CHANNEL_USERNAME
from config.constants import DEFAULT_MESSAGES, States

logger = logging.getLogger(__name__)

class VerificationStates(StatesGroup):
    waiting_verification = State()

async def start_command(message: types.Message, state: FSMContext, db: Database):
    """Handler para o comando /start"""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    # Se o usuário não existir, cria um novo registro
    if not user_data:
        user_data = {
            "id": user_id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "in_channel": False
        }
        await db.save_user(user_id, user_data)
    
    # Se o usuário já está verificado, mostra menu principal
    if user_data.get("in_channel", False):
        await show_main_menu(message, state)
        return
    
    # Caso contrário, solicita verificação do canal
    await request_channel_verification(message, state)

async def request_channel_verification(message: types.Message, state: FSMContext):
    """Solicita ao usuário verificação de participação no canal"""
    # Cria teclado com botão para o canal e verificação
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="🔗 Entrar no Canal", url=CHANNEL_LINK),
        types.InlineKeyboardButton(text="✅ Verifiquei", callback_data="verify_channel")
    )
    
    # Envia mensagem com solicitação
    await message.answer(DEFAULT_MESSAGES["welcome"], reply_markup=keyboard)
    
    # Define estado para aguardar verificação
    await VerificationStates.waiting_verification.set()

async def verify_channel_callback(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    """Handler para o callback de verificação do canal"""
    user_id = callback_query.from_user.id
    
    # Verifica se o usuário está no canal
    is_member = await is_user_in_channel(bot, user_id, CHANNEL_ID)
    
    if is_member:
        # Atualiza status do usuário
        await db.set_user_in_channel(user_id, True)
        
        # Notifica o usuário
        await callback_query.answer(text="✅ Verificação concluída!", show_alert=True)
        
        # Mostra o menu principal
        await show_main_menu(callback_query.message, state)
    else:
        # Notifica que o usuário não está no canal
        await callback_query.answer(
            text=DEFAULT_MESSAGES["not_in_channel"],
            show_alert=True
        )

async def show_main_menu(message: types.Message, state: FSMContext):
    """Mostra o menu principal após verificação"""
    # Reseta o estado
    await state.finish()
    
    # Cria teclado com opções principais
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="🤖 Criar seu Bot", callback_data="create_bot"),
        types.InlineKeyboardButton(text="📝 Meus bots", callback_data="my_bots"),
    )
    keyboard.add(
        types.InlineKeyboardButton(text="ℹ️ Como funciona", callback_data="how_it_works")
    )
    
    # Envia mensagem com menu
    await message.answer(
        DEFAULT_MESSAGES["bot_description"],
        reply_markup=keyboard
    )

def register_verification_handlers(dp: Dispatcher, bot: Bot, db: Database):
    """Registra os handlers de verificação"""
    dp.register_message_handler(
        lambda message, state: start_command(message, state, db),
        commands=["start"],
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda callback, state: verify_channel_callback(callback, state, bot, db),
        lambda c: c.data == "verify_channel",
        state=VerificationStates.waiting_verification
    )