#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Handlers para interações dos usuários com o bot gerenciador
"""

import logging
from aiogram import Dispatcher, Bot, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from core.database import Database
from core.bot_manager import BotManager
from core.utils import build_bots_list_keyboard, build_menu_keyboard, create_bot_info_text
from config.constants import DEFAULT_MESSAGES, States

logger = logging.getLogger(__name__)

class BotCreationStates(StatesGroup):
    waiting_token = State()

async def how_it_works_callback(callback_query: types.CallbackQuery):
    """Handler para o callback de 'Como funciona'"""
    # Texto explicativo sobre como o sistema funciona
    text = (
        "ℹ️ <b>Como funciona o Zenyx VIPs</b>\n\n"
        "Este sistema permite que você crie e gerencie seu próprio bot para vendas de acessos VIP no Telegram.\n\n"
        "<b>Passo a passo:</b>\n"
        "1. Crie um bot pelo @BotFather\n"
        "2. Copie o token e adicione aqui\n"
        "3. Configure mensagens, planos e integrações de pagamento\n"
        "4. Adicione seu bot a grupos/canais para gerenciar\n"
        "5. Comece a vender acessos VIP!\n\n"
        "Para começar, clique em <b>🤖 Criar seu Bot</b>"
    )
    
    # Botão para voltar
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_menu"))
    
    # Edita a mensagem com a explicação
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback_query.answer()

async def create_bot_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de 'Criar seu Bot'"""
    # Responde ao callback
    await callback_query.answer()
    
    # Envia instruções para criar um bot
    await callback_query.message.edit_text(
        DEFAULT_MESSAGES["bot_creation_instructions"],
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_menu")
        )
    )
    
    # Define o estado para aguardar o token
    await BotCreationStates.waiting_token.set()

async def token_message(message: types.Message, state: FSMContext, bot_manager: BotManager):
    """Handler para receber o token do bot"""
    token = message.text.strip()
    user_id = message.from_user.id
    
    # Notifica que o bot está sendo iniciado
    status_message = await message.answer(DEFAULT_MESSAGES["bot_starting"])
    
    # Tenta criar o bot
    bot_data = await bot_manager.create_user_bot(user_id, token)
    
    if bot_data:
        username = bot_data.get("username", "")
        
        # Notifica que o bot foi iniciado com sucesso
        await status_message.edit_text(
            DEFAULT_MESSAGES["bot_started"].format(username=username)
        )
        
        # Envia mensagem com botão para acessar o bot
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                text=f"🚀 Iniciar @{username}",
                url=f"https://t.me/{username}"
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                text="🔙 Voltar ao Menu",
                callback_data="back_to_menu"
            )
        )
        
        await message.answer(
            DEFAULT_MESSAGES["bot_created"].format(username=username),
            reply_markup=keyboard
        )
        
        # Reseta o estado
        await state.finish()
    else:
        # Notifica erro e solicita novo token
        await status_message.edit_text(
            "❌ Token inválido ou bot indisponível.\n\n"
            "Por favor, verifique se o token está correto e tente novamente.\n\n"
            "Para cancelar, clique em 'Voltar'.",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_menu")
            )
        )
        
        # Mantém o estado para aguardar um novo token
        await BotCreationStates.waiting_token.set()

async def my_bots_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_manager: BotManager):
    """Handler para o callback de 'Meus bots'"""
    user_id = callback_query.from_user.id
    
    # Obtém os bots do usuário
    user_bots = await bot_manager.get_user_bots(user_id)
    
    if user_bots:
        # Cria teclado com a lista de bots
        keyboard = build_bots_list_keyboard(user_bots)
        
        # Mostra a lista de bots
        await callback_query.message.edit_text(
            "🤖 Seus Bots",
            reply_markup=keyboard
        )
    else:
        # Se não tiver bots, mostra mensagem e botão para criar
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(text="➕ Criar Bot", callback_data="create_bot"),
            types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_menu")
        )
        
        await callback_query.message.edit_text(
            "🤖 Você ainda não tem bots criados.\n\n"
            "Clique em 'Criar Bot' para começar!",
            reply_markup=keyboard
        )
    
    await callback_query.answer()

async def select_bot_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_manager: BotManager):
    """Handler para selecionar um bot da lista"""
    bot_id = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id
    
    # Obtém dados do bot
    bot_data = await bot_manager.get_user_bot(bot_id)
    
    if bot_data and str(bot_data.get("user_id")) == str(user_id):
        # Mostra informações do bot e opções
        text = create_bot_info_text(bot_data)
        keyboard = build_menu_keyboard(user_id, bot_data)
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    else:
        # Bot não encontrado ou não pertence ao usuário
        await callback_query.answer("❌ Bot não encontrado.", show_alert=True)
    
    await callback_query.answer()

async def pause_bot_callback(callback_query: types.CallbackQuery, bot_manager: BotManager):
    """Handler para pausar um bot"""
    bot_id = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id
    
    # Obtém dados do bot
    bot_data = await bot_manager.get_user_bot(bot_id)
    
    if bot_data and str(bot_data.get("user_id")) == str(user_id):
        # Pausa o bot
        success = await bot_manager.pause_user_bot(bot_id)
        
        if success:
            await callback_query.answer("✅ Bot pausado com sucesso!", show_alert=True)
            
            # Atualiza dados do bot
            bot_data = await bot_manager.get_user_bot(bot_id)
            
            # Atualiza mensagem com status atualizado
            text = create_bot_info_text(bot_data)
            keyboard = build_menu_keyboard(user_id, bot_data)
            
            await callback_query.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback_query.answer("❌ Erro ao pausar o bot.", show_alert=True)
    else:
        await callback_query.answer("❌ Bot não encontrado.", show_alert=True)

async def resume_bot_callback(callback_query: types.CallbackQuery, bot_manager: BotManager):
    """Handler para ativar um bot"""
    bot_id = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id
    
    # Obtém dados do bot
    bot_data = await bot_manager.get_user_bot(bot_id)
    
    if bot_data and str(bot_data.get("user_id")) == str(user_id):
        # Ativa o bot
        success = await bot_manager.resume_user_bot(bot_id)
        
        if success:
            await callback_query.answer("✅ Bot ativado com sucesso!", show_alert=True)
            
            # Atualiza dados do bot
            bot_data = await bot_manager.get_user_bot(bot_id)
            
            # Atualiza mensagem com status atualizado
            text = create_bot_info_text(bot_data)
            keyboard = build_menu_keyboard(user_id, bot_data)
            
            await callback_query.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback_query.answer("❌ Erro ao ativar o bot.", show_alert=True)
    else:
        await callback_query.answer("❌ Bot não encontrado.", show_alert=True)

async def update_token_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para atualizar o token de um bot"""
    bot_id = callback_query.data.split(':')[1]
    
    # Guarda o ID do bot no estado
    await state.update_data(bot_id=bot_id)
    
    # Solicita o novo token
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🔙 Cancelar", callback_data=f"select_bot:{bot_id}"))
    
    await callback_query.message.edit_text(
        "🔄 <b>Atualizar Token</b>\n\n"
        "Envie o novo token do seu bot gerado pelo @BotFather.\n\n"
        "⚠️ <b>Atenção:</b> Isso irá reiniciar seu bot. "
        "Todas as configurações serão mantidas.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Define o estado para aguardar o novo token
    await BotCreationStates.waiting_token.set()
    
    await callback_query.answer()

async def delete_bot_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para confirmar exclusão de um bot"""
    bot_id = callback_query.data.split(':')[1]
    
    # Guarda o ID do bot no estado
    await state.update_data(bot_id=bot_id)
    
    # Solicita confirmação
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="✅ Sim, excluir", callback_data=f"confirm_delete:{bot_id}"),
        types.InlineKeyboardButton(text="❌ Cancelar", callback_data=f"select_bot:{bot_id}")
    )
    
    await callback_query.message.edit_text(
        "🗑 <b>Excluir Bot</b>\n\n"
        "Tem certeza que deseja excluir este bot?\n\n"
        "⚠️ <b>Atenção:</b> Esta ação não pode ser desfeita. "
        "Todas as configurações, planos e mensagens serão perdidos.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await callback_query.answer()

async def confirm_delete_bot_callback(callback_query: types.CallbackQuery, bot_manager: BotManager):
    """Handler para confirmar exclusão de um bot"""
    bot_id = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id
    
    # Obtém dados do bot
    bot_data = await bot_manager.get_user_bot(bot_id)
    
    if bot_data and str(bot_data.get("user_id")) == str(user_id):
        # Exclui o bot
        success = await bot_manager.delete_user_bot(bot_id)
        
        if success:
            await callback_query.answer("✅ Bot excluído com sucesso!", show_alert=True)
            
            # Volta para a lista de bots
            await my_bots_callback(callback_query, None, bot_manager)
        else:
            await callback_query.answer("❌ Erro ao excluir o bot.", show_alert=True)
            
            # Volta para a seleção do bot
            await select_bot_callback(callback_query, None, bot_manager)
    else:
        await callback_query.answer("❌ Bot não encontrado.", show_alert=True)

async def back_to_menu_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para voltar ao menu principal"""
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
    
    # Edita a mensagem com o menu principal
    await callback_query.message.edit_text(
        DEFAULT_MESSAGES["bot_description"],
        reply_markup=keyboard
    )
    
    await callback_query.answer()

async def back_to_bots_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_manager: BotManager):
    """Handler para voltar à lista de bots"""
    await my_bots_callback(callback_query, state, bot_manager)

def register_user_handlers(dp: Dispatcher, bot: Bot, bot_manager: BotManager, db: Database):
    """Registra os handlers para usuários"""
    # Callback handlers
    dp.register_callback_query_handler(
        how_it_works_callback,
        lambda c: c.data == "how_it_works",
        state="*"
    )
    
    dp.register_callback_query_handler(
        create_bot_callback,
        lambda c: c.data == "create_bot",
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c, s: my_bots_callback(c, s, bot_manager),
        lambda c: c.data == "my_bots",
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c, s: select_bot_callback(c, s, bot_manager),
        lambda c: c.data.startswith("select_bot:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c: pause_bot_callback(c, bot_manager),
        lambda c: c.data.startswith("pause_bot:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c: resume_bot_callback(c, bot_manager),
        lambda c: c.data.startswith("resume_bot:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        update_token_callback,
        lambda c: c.data.startswith("update_token:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        delete_bot_callback,
        lambda c: c.data.startswith("delete_bot:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c: confirm_delete_bot_callback(c, bot_manager),
        lambda c: c.data.startswith("confirm_delete:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        back_to_menu_callback,
        lambda c: c.data == "back_to_menu",
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c, s: back_to_bots_callback(c, s, bot_manager),
        lambda c: c.data == "back_to_bots",
        state="*"
    )
    
    # Message handlers
    dp.register_message_handler(
        lambda m, s: token_message(m, s, bot_manager),
        state=BotCreationStates.waiting_token
    )