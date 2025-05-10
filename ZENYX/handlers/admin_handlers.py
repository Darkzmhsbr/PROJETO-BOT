#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Handlers para interações de administradores com o bot gerenciador
"""

import logging
from aiogram import Dispatcher, Bot, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from core.database import Database
from core.bot_manager import BotManager
from config.settings import ADMIN_IDS

logger = logging.getLogger(__name__)

class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_broadcast_confirm = State()

async def admin_command(message: types.Message, state: FSMContext, db: Database):
    """Handler para o comando /admin"""
    user_id = message.from_user.id
    
    # Verifica se o usuário é admin
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Você não tem permissão para usar este comando.")
        return
    
    # Mostra menu admin
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="📊 Estatísticas", callback_data="admin_stats"),
        types.InlineKeyboardButton(text="📣 Enviar mensagem para todos", callback_data="admin_broadcast"),
        types.InlineKeyboardButton(text="⚙️ Gerenciar bots", callback_data="admin_manage_bots")
    )
    
    await message.answer(
        "🔐 <b>Painel de Administração</b>\n\n"
        "Selecione uma opção:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def admin_stats_callback(callback_query: types.CallbackQuery, db: Database):
    """Handler para o callback de estatísticas"""
    # Obtém estatísticas do sistema
    all_bots = await db.get_all_user_bots()
    active_bots = len([bot for bot in all_bots if bot.get("status") == "active"])
    
    # Obtém todos os usuários únicos
    unique_users = set()
    for bot in all_bots:
        unique_users.add(bot.get("user_id"))
    
    text = (
        "📊 <b>Estatísticas do Sistema</b>\n\n"
        f"👥 Total de usuários: {len(unique_users)}\n"
        f"🤖 Total de bots: {len(all_bots)}\n"
        f"🟢 Bots ativos: {active_bots}\n"
        f"🔴 Bots inativos: {len(all_bots) - active_bots}\n"
    )
    
    # Botão para voltar
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="admin_back"))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback_query.answer()

async def admin_broadcast_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de broadcast"""
    # Solicita a mensagem para enviar
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_back"))
    
    await callback_query.message.edit_text(
        "📣 <b>Enviar Mensagem para Todos</b>\n\n"
        "Digite a mensagem que deseja enviar para todos os usuários.\n\n"
        "Você pode usar formatação HTML.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Define o estado para aguardar a mensagem
    await AdminStates.waiting_broadcast.set()
    
    await callback_query.answer()

async def admin_broadcast_message(message: types.Message, state: FSMContext, db: Database):
    """Handler para receber a mensagem de broadcast"""
    # Salva a mensagem no estado
    await state.update_data(broadcast_message=message.html_text)
    
    # Obtém todos os usuários únicos
    all_bots = await db.get_all_user_bots()
    unique_users = set()
    for bot in all_bots:
        unique_users.add(bot.get("user_id"))
    
    # Solicita confirmação
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="✅ Confirmar", callback_data="admin_broadcast_confirm"),
        types.InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_back")
    )
    
    await message.answer(
        "📣 <b>Confirmar Mensagem</b>\n\n"
        f"A mensagem será enviada para <b>{len(unique_users)}</b> usuários.\n\n"
        "<b>Prévia:</b>\n"
        f"{message.html_text}\n\n"
        "Deseja confirmar o envio?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Define o estado para aguardar confirmação
    await AdminStates.waiting_broadcast_confirm.set()

async def admin_broadcast_confirm_callback(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    """Handler para confirmar o envio do broadcast"""
    # Obtém a mensagem do estado
    data = await state.get_data()
    broadcast_message = data.get("broadcast_message")
    
    # Obtém todos os usuários únicos
    all_bots = await db.get_all_user_bots()
    unique_users = set()
    for bot_data in all_bots:
        unique_users.add(bot_data.get("user_id"))
    
    # Notifica início do envio
    await callback_query.message.edit_text(
        "📣 <b>Enviando Mensagem...</b>\n\n"
        f"Enviando para {len(unique_users)} usuários.",
        parse_mode="HTML"
    )
    
    # Contador de sucessos e falhas
    success_count = 0
    fail_count = 0
    
    # Envia a mensagem para cada usuário
    for user_id in unique_users:
        try:
            await bot.send_message(user_id, broadcast_message, parse_mode="HTML")
            success_count += 1
        except Exception as e:
            logger.error(f"Erro ao enviar broadcast para {user_id}: {e}", exc_info=True)
            fail_count += 1
    
    # Notifica conclusão
    await callback_query.message.edit_text(
        "📣 <b>Mensagem Enviada</b>\n\n"
        f"✅ Enviada com sucesso para {success_count} usuários.\n"
        f"❌ Falha ao enviar para {fail_count} usuários.",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(text="🔙 Voltar", callback_data="admin_back")
        )
    )
    
    # Reseta o estado
    await state.finish()

async def admin_manage_bots_callback(callback_query: types.CallbackQuery, db: Database):
    """Handler para o callback de gerenciar bots"""
    # Obtém todos os bots
    all_bots = await db.get_all_user_bots()
    
    # Cria lista de bots com paginação
    page = 1
    items_per_page = 5
    total_pages = (len(all_bots) + items_per_page - 1) // items_per_page
    
    # Slice dos bots para a página atual
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_bots = all_bots[start_idx:end_idx]
    
    # Cria teclado com bots e navegação
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for bot in page_bots:
        username = bot.get("username", "")
        bot_id = bot.get("id", "")
        status = "🟢" if bot.get("status") == "active" else "🔴"
        
        keyboard.add(types.InlineKeyboardButton(
            text=f"{status} @{username} (ID: {bot_id})",
            callback_data=f"admin_bot:{bot_id}"
        ))
    
    # Adiciona botões de navegação
    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton(
            text="⬅️ Anterior", callback_data=f"admin_bots_page:{page-1}"
        ))
    
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton(
            text="➡️ Próxima", callback_data=f"admin_bots_page:{page+1}"
        ))
    
    if nav_buttons:
        keyboard.row(*nav_buttons)
    
    # Botão para voltar
    keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="admin_back"))
    
    await callback_query.message.edit_text(
        f"⚙️ <b>Gerenciar Bots</b> (Página {page}/{total_pages})\n\n"
        f"Total de bots: {len(all_bots)}\n\n"
        "Selecione um bot para gerenciar:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await callback_query.answer()

async def admin_bot_page_callback(callback_query: types.CallbackQuery, db: Database):
    """Handler para navegar entre páginas de bots"""
    page = int(callback_query.data.split(':')[1])
    
    # Chama a função de listagem com a página atualizada
    await admin_manage_bots_callback(callback_query, db)

async def admin_bot_callback(callback_query: types.CallbackQuery, db: Database, bot_manager: BotManager):
    """Handler para gerenciar um bot específico"""
    bot_id = callback_query.data.split(':')[1]
    
    # Obtém dados do bot
    bot_data = await bot_manager.get_user_bot(bot_id)
    
    if not bot_data:
        await callback_query.answer("❌ Bot não encontrado.", show_alert=True)
        return
    
    # Obtém dados do usuário
    user_id = bot_data.get("user_id")
    user_data = await db.get_user(user_id)
    
    # Prepara informações do bot
    username = bot_data.get("username", "")
    status = "🟢 Ativo" if bot_data.get("status") == "active" else "🔴 Inativo"
    
    text = (
        f"🤖 <b>Bot: @{username}</b>\n\n"
        f"ID: {bot_id}\n"
        f"Status: {status}\n"
        f"Dono: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n"
        f"Username do dono: @{user_data.get('username', '')}\n"
        f"ID do dono: {user_id}\n"
    )
    
    # Cria teclado com opções
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    # Botão para ativar/desativar
    is_active = bot_data.get("status") == "active"
    status_text = "🔴 Desativar Bot" if is_active else "🟢 Ativar Bot"
    status_action = f"admin_bot_pause:{bot_id}" if is_active else f"admin_bot_resume:{bot_id}"
    keyboard.add(types.InlineKeyboardButton(text=status_text, callback_data=status_action))
    
    # Botões para outras ações
    keyboard.add(
        types.InlineKeyboardButton(text="🗑 Excluir Bot", callback_data=f"admin_bot_delete:{bot_id}"),
        types.InlineKeyboardButton(text="🔙 Voltar", callback_data="admin_manage_bots")
    )
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback_query.answer()

async def admin_bot_pause_callback(callback_query: types.CallbackQuery, bot_manager: BotManager):
    """Handler para desativar um bot"""
    bot_id = callback_query.data.split(':')[1]
    
    # Pausa o bot
    success = await bot_manager.pause_user_bot(bot_id)
    
    if success:
        await callback_query.answer("✅ Bot desativado com sucesso!", show_alert=True)
    else:
        await callback_query.answer("❌ Erro ao desativar o bot.", show_alert=True)
    
    # Volta para a página do bot
    callback_query.data = f"admin_bot:{bot_id}"
    await admin_bot_callback(callback_query, None, bot_manager)

async def admin_bot_resume_callback(callback_query: types.CallbackQuery, bot_manager: BotManager):
    """Handler para ativar um bot"""
    bot_id = callback_query.data.split(':')[1]
    
    # Ativa o bot
    success = await bot_manager.resume_user_bot(bot_id)
    
    if success:
        await callback_query.answer("✅ Bot ativado com sucesso!", show_alert=True)
    else:
        await callback_query.answer("❌ Erro ao ativar o bot.", show_alert=True)
    
    # Volta para a página do bot
    callback_query.data = f"admin_bot:{bot_id}"
    await admin_bot_callback(callback_query, None, bot_manager)

async def admin_bot_delete_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para confirmar exclusão de um bot"""
    bot_id = callback_query.data.split(':')[1]
    
    # Solicita confirmação
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="✅ Sim, excluir", callback_data=f"admin_bot_delete_confirm:{bot_id}"),
        types.InlineKeyboardButton(text="❌ Cancelar", callback_data=f"admin_bot:{bot_id}")
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

async def admin_bot_delete_confirm_callback(callback_query: types.CallbackQuery, bot_manager: BotManager):
    """Handler para confirmar exclusão de um bot"""
    bot_id = callback_query.data.split(':')[1]
    
    # Exclui o bot
    success = await bot_manager.delete_user_bot(bot_id)
    
    if success:
        await callback_query.answer("✅ Bot excluído com sucesso!", show_alert=True)
        
        # Volta para a lista de bots
        await admin_manage_bots_callback(callback_query, None)
    else:
        await callback_query.answer("❌ Erro ao excluir o bot.", show_alert=True)
        
        # Volta para a página do bot
        callback_query.data = f"admin_bot:{bot_id}"
        await admin_bot_callback(callback_query, None, bot_manager)

async def admin_back_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para voltar ao menu admin"""
    # Reseta o estado
    await state.finish()
    
    # Volta para o menu admin
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="📊 Estatísticas", callback_data="admin_stats"),
        types.InlineKeyboardButton(text="📣 Enviar mensagem para todos", callback_data="admin_broadcast"),
        types.InlineKeyboardButton(text="⚙️ Gerenciar bots", callback_data="admin_manage_bots")
    )
    
    await callback_query.message.edit_text(
        "🔐 <b>Painel de Administração</b>\n\n"
        "Selecione uma opção:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    await callback_query.answer()

def register_admin_handlers(dp: Dispatcher, bot: Bot, bot_manager: BotManager, db: Database):
    """Registra os handlers para administradores"""
    # Comando admin
    dp.register_message_handler(
        lambda message, state: admin_command(message, state, db),
        commands=["admin"],
        state="*"
    )
    
    # Callbacks
    dp.register_callback_query_handler(
        lambda c: admin_stats_callback(c, db),
        lambda c: c.data == "admin_stats",
        state="*"
    )
    
    dp.register_callback_query_handler(
        admin_broadcast_callback,
        lambda c: c.data == "admin_broadcast",
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c: admin_manage_bots_callback(c, db),
        lambda c: c.data == "admin_manage_bots",
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c: admin_bot_page_callback(c, db),
        lambda c: c.data.startswith("admin_bots_page:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c: admin_bot_callback(c, db, bot_manager),
        lambda c: c.data.startswith("admin_bot:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c: admin_bot_pause_callback(c, bot_manager),
        lambda c: c.data.startswith("admin_bot_pause:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c: admin_bot_resume_callback(c, bot_manager),
        lambda c: c.data.startswith("admin_bot_resume:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        admin_bot_delete_callback,
        lambda c: c.data.startswith("admin_bot_delete:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        lambda c: admin_bot_delete_confirm_callback(c, bot_manager),
        lambda c: c.data.startswith("admin_bot_delete_confirm:"),
        state="*"
    )
    
    dp.register_callback_query_handler(
        admin_back_callback,
        lambda c: c.data == "admin_back",
        state="*"
    )
    
    # Estados
    dp.register_message_handler(
        lambda m, s: admin_broadcast_message(m, s, db),
        state=AdminStates.waiting_broadcast
    )
    
    dp.register_callback_query_handler(
        lambda c, s: admin_broadcast_confirm_callback(c, s, bot, db),
        lambda c: c.data == "admin_broadcast_confirm",
        state=AdminStates.waiting_broadcast_confirm
    )