#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Handlers para os bots dos usuários
"""

import logging
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from config.settings import get_redis_url
from core.database import Database
from core.bot_manager import UserBot
from core.utils import (
    is_user_in_channel, 
    build_channel_info_text, 
    get_period_timestamps,
    format_price
)
from user_bot.message_config import (
    get_welcome_messages,
    save_message,
    update_message_order
)
from user_bot.payment import (
    save_pushinpay_token,
    get_pushinpay_token,
    create_payment
)
from user_bot.plans import (
    get_plans,
    save_plan,
    delete_plan,
    format_plan_info
)
from user_bot.upsell import (
    get_upsell_config,
    save_upsell_config,
    toggle_upsell
)
from user_bot.order_bump import (
    get_order_bump_config,
    save_order_bump_config,
    toggle_order_bump
)
from user_bot.remarketing import (
    send_remarketing_message,
    prepare_remarketing_message
)
from user_bot.metrics import get_sales_metrics
from user_bot.support import save_support_config, get_support_config

logger = logging.getLogger(__name__)

class BotStates(StatesGroup):
    # Estados para configuração de mensagens
    configuring_messages = State()
    waiting_message_type = State()
    waiting_message_text = State()
    waiting_message_media = State()
    waiting_message_media_caption = State()
    
    # Estados para configuração da PushinPay
    waiting_pushinpay_token = State()
    
    # Estados para configuração de chat VIP
    waiting_chat_id = State()
    
    # Estados para configuração de suporte
    waiting_support_username = State()
    
    # Estados para configuração de upsell
    waiting_upsell_text = State()
    waiting_upsell_button_text = State()
    waiting_upsell_price = State()
    waiting_upsell_link = State()
    
    # Estados para configuração de order bump
    waiting_order_bump_text = State()
    waiting_order_bump_price = State()
    waiting_order_bump_link = State()
    
    # Estados para remarketing
    waiting_remarketing_target = State()
    waiting_remarketing_promotion = State()
    waiting_remarketing_plan = State()
    waiting_remarketing_price = State()
    waiting_remarketing_message = State()
    
    # Estados para criação de planos
    waiting_plan_name = State()
    waiting_plan_price = State()
    waiting_plan_duration = State()

async def start_command(message: types.Message, state: FSMContext, user_bot: UserBot):
    """Handler para o comando /start nos bots dos usuários"""
    user_id = message.from_user.id
    bot_owner_id = user_bot.user_id
    
    # Verifica se é o dono do bot
    if str(user_id) == str(bot_owner_id):
        await show_admin_menu(message, user_bot)
        return
    
    # Para usuários normais, verifica se há mensagens de boas-vindas configuradas
    welcome_messages = await get_welcome_messages(user_bot)
    
    if welcome_messages:
        # Envia mensagens de boas-vindas na ordem configurada
        for msg in welcome_messages:
            msg_type = msg.get("type", "text")
            
            if msg_type == "text":
                await message.answer(msg.get("text", ""), parse_mode="HTML")
            elif msg_type == "media" or msg_type == "media_with_text":
                media_id = msg.get("media_id")
                caption = msg.get("text", "")
                
                if media_id:
                    try:
                        # Determina o tipo de mídia
                        if msg.get("media_type") == "photo":
                            await message.answer_photo(media_id, caption=caption, parse_mode="HTML")
                        elif msg.get("media_type") == "video":
                            await message.answer_video(media_id, caption=caption, parse_mode="HTML")
                        elif msg.get("media_type") == "animation":
                            await message.answer_animation(media_id, caption=caption, parse_mode="HTML")
                        else:
                            # Fallback para documentos
                            await message.answer_document(media_id, caption=caption, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Erro ao enviar mídia: {e}", exc_info=True)
                        await message.answer(caption, parse_mode="HTML")
    else:
        # Mensagem padrão se não houver mensagens configuradas
        await message.answer(
            f"Olá! Bem-vindo ao bot @{user_bot.username}."
        )
    
    # Mostra planos disponíveis
    plans = await get_plans(user_bot)
    
    if plans:
        # Cria teclado com os planos disponíveis
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        for plan in plans:
            plan_name = plan.get("name", "Plano")
            plan_price = plan.get("price", 0)
            plan_id = plan.get("id", "")
            
            keyboard.add(types.InlineKeyboardButton(
                text=f"{plan_name} - {format_price(plan_price)}",
                callback_data=f"plan:{plan_id}"
            ))
        
        # Verifica se há order bump configurado
        order_bump = await get_order_bump_config(user_bot)
        if order_bump and order_bump.get("active", False):
            # Adiciona botão de order bump
            keyboard.add(types.InlineKeyboardButton(
                text=f"{order_bump.get('text', 'Order Bump')} - {format_price(order_bump.get('price', 0))}",
                callback_data="order_bump"
            ))
        
        await message.answer(
            "🛒 <b>Planos Disponíveis</b>\n\n"
            "Selecione um plano para assinar:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

async def show_admin_menu(message: types.Message, user_bot: UserBot):
    """Mostra o menu de administração para o dono do bot"""
    # Obtém o nome de usuário do bot
    bot_username = await user_bot.get_username()
    
    # Mensagem de boas-vindas para o administrador
    text = (
        f"👋 Olá @{message.from_user.username} e bem-vindo ao @{bot_username}!\n\n"
        f"👨‍💼 Você é o administrador deste bot!"
    )
    
    # Cria teclado com opções de administração
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="📝 Configurar mensagens", callback_data="config_messages"),
        types.InlineKeyboardButton(text="💰 Integrar Pushin Pay", callback_data="config_pushinpay")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="👥 Adicionar canal/grupo", callback_data="config_chat"),
        types.InlineKeyboardButton(text="📞 Configurar suporte", callback_data="config_support")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="📊 Métricas de Vendas", callback_data="sales_metrics"),
        types.InlineKeyboardButton(text="🛍 Adicionar Upsell", callback_data="config_upsell")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="💱 Adicionar Order Bump", callback_data="config_order_bump"),
        types.InlineKeyboardButton(text="📤 Remarketing", callback_data="config_remarketing")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="🎯 Criar planos", callback_data="config_plans")
    )
    
    await message.answer(text, reply_markup=keyboard)

# Handlers para configuração de mensagens

async def config_messages_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de configuração de mensagens"""
    # Obtém as mensagens configuradas
    messages = await get_welcome_messages(user_bot)
    
    # Prepara o texto da mensagem
    text = (
        "⚙️ Configuração de Boas-vindas\n"
        f"📝 Total de mensagens: {len(messages)}\n\n"
        "Gerencie as mensagens de boas-vindas que seus usuários receberão ao iniciar o bot.\n\n"
        "ℹ️ As mensagens serão enviadas na ordem configurada."
    )
    
    # Cria teclado com opções
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="📝 Nova mensagem", callback_data="new_message"),
        types.InlineKeyboardButton(text="👀 Visualizar todas", callback_data="view_messages")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="📝 Editar mensagens", callback_data="edit_messages"),
        types.InlineKeyboardButton(text="📤 Ordem das mensagens", callback_data="message_order")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
    )
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()

async def new_message_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de nova mensagem"""
    # Solicita o tipo de mensagem
    text = (
        "📝 Nova Mensagem de Boas-vindas\n\n"
        "Escolha o tipo de conteúdo para esta mensagem:"
    )
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="📝 Apenas texto", callback_data="new_text_message"),
        types.InlineKeyboardButton(text="🖼 Mídia + texto", callback_data="new_media_message"),
        types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages")
    )
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()

async def new_text_message_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de nova mensagem de texto"""
    # Solicita o texto da mensagem
    text = "✏️ Digite o texto da mensagem de boas-vindas:"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_messages"))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    # Define o estado para aguardar o texto
    await state.update_data(message_type="text")
    await BotStates.waiting_message_text.set()
    
    await callback_query.answer()

async def new_media_message_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de nova mensagem com mídia"""
    # Solicita a mídia
    text = "🖼 Envie a mídia (foto, vídeo ou GIF):"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_messages"))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    # Define o estado para aguardar a mídia
    await state.update_data(message_type="media_with_text")
    await BotStates.waiting_message_media.set()
    
    await callback_query.answer()

async def message_text_handler(message: types.Message, state: FSMContext, user_bot: UserBot):
    """Handler para receber o texto da mensagem"""
    # Obtém dados do estado
    data = await state.get_data()
    message_type = data.get("message_type", "text")
    
    if message_type == "media_with_text":
        # Caso seja um texto para acompanhar mídia
        media_id = data.get("media_id")
        media_type = data.get("media_type")
        
        # Salva a mensagem completa
        message_data = {
            "type": "media_with_text",
            "text": message.text,
            "media_id": media_id,
            "media_type": media_type
        }
        
        await save_message(user_bot, message_data)
        
        # Notifica sucesso
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages"))
        
        await message.answer(
            "✅ Mensagem com mídia salva com sucesso!",
            reply_markup=keyboard
        )
    else:
        # Caso seja apenas texto
        message_data = {
            "type": "text",
            "text": message.text
        }
        
        await save_message(user_bot, message_data)
        
        # Notifica sucesso
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages"))
        
        await message.answer(
            "✅ Mensagem de texto salva com sucesso!",
            reply_markup=keyboard
        )
    
    # Reseta o estado
    await state.finish()

async def message_media_handler(message: types.Message, state: FSMContext):
    """Handler para receber a mídia da mensagem"""
    # Identifica o tipo de mídia
    media_id = None
    media_type = None
    
    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"
    elif message.animation:
        media_id = message.animation.file_id
        media_type = "animation"
    elif message.document:
        media_id = message.document.file_id
        media_type = "document"
    
    if media_id:
        # Salva a mídia no estado
        await state.update_data(media_id=media_id, media_type=media_type)
        
        # Solicita o texto que acompanhará a mídia
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_messages"))
        
        await message.answer(
            "✅ Mídia recebida com sucesso!\n\n"
            "Agora, envie o texto que acompanhará esta mídia "
            "(ou envie /pular para usar apenas a mídia):",
            reply_markup=keyboard
        )
        
        # Atualiza o estado para aguardar o texto
        await BotStates.waiting_message_text.set()
    else:
        # Mídia não reconhecida
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages"))
        
        await message.answer(
            "❌ Tipo de mídia não suportado.\n\n"
            "Por favor, envie uma foto, vídeo ou GIF.",
            reply_markup=keyboard
        )

async def view_messages_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de visualizar mensagens"""
    # Obtém as mensagens configuradas
    messages = await get_welcome_messages(user_bot)
    
    if not messages:
        # Não há mensagens configuradas
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages"))
        
        await callback_query.message.edit_text(
            "❌ Não há mensagens configuradas.",
            reply_markup=keyboard
        )
        await callback_query.answer()
        return
    
    # Envia as mensagens em sequência
    await callback_query.answer("Enviando visualização das mensagens...")
    
    for msg in messages:
        msg_type = msg.get("type", "text")
        
        if msg_type == "text":
            await callback_query.message.answer(msg.get("text", ""), parse_mode="HTML")
        elif msg_type == "media" or msg_type == "media_with_text":
            media_id = msg.get("media_id")
            caption = msg.get("text", "")
            
            if media_id:
                try:
                    # Determina o tipo de mídia
                    if msg.get("media_type") == "photo":
                        await callback_query.message.answer_photo(media_id, caption=caption, parse_mode="HTML")
                    elif msg.get("media_type") == "video":
                        await callback_query.message.answer_video(media_id, caption=caption, parse_mode="HTML")
                    elif msg.get("media_type") == "animation":
                        await callback_query.message.answer_animation(media_id, caption=caption, parse_mode="HTML")
                    else:
                        # Fallback para documentos
                        await callback_query.message.answer_document(media_id, caption=caption, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Erro ao enviar mídia: {e}", exc_info=True)
                    await callback_query.message.answer(caption, parse_mode="HTML")
    
    # Botão para voltar
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages"))
    
    await callback_query.message.answer(
        "👀 Visualização das Mensagens de Boas-vindas\n\n"
        "Mensagens enviadas em sequência.",
        reply_markup=keyboard
    )

async def edit_messages_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de editar mensagens"""
    # Obtém as mensagens configuradas
    messages = await get_welcome_messages(user_bot)
    
    if not messages:
        # Não há mensagens configuradas
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages"))
        
        await callback_query.message.edit_text(
            "❌ Não há mensagens configuradas.",
            reply_markup=keyboard
        )
        await callback_query.answer()
        return
    
    # Cria teclado com as mensagens
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for i, msg in enumerate(messages):
        msg_type = msg.get("type", "text")
        msg_id = msg.get("id", "")
        
        if msg_type == "text":
            # Limita a preview do texto
            text = msg.get("text", "")
            if len(text) > 30:
                text = text[:30] + "..."
            keyboard.add(types.InlineKeyboardButton(
                text=f"Mensagem de texto: {text}",
                callback_data=f"edit_message:{msg_id}"
            ))
        else:
            keyboard.add(types.InlineKeyboardButton(
                text=f"Mensagem de mídia+texto",
                callback_data=f"edit_message:{msg_id}"
            ))
    
    # Adiciona botão para apagar todas as mensagens
    keyboard.add(types.InlineKeyboardButton(
        text="🗑 Apagar todas as mensagens",
        callback_data="delete_all_messages"
    ))
    
    # Adiciona botão para voltar
    keyboard.add(types.InlineKeyboardButton(
        text="🔙 Voltar",
        callback_data="config_messages"
    ))
    
    await callback_query.message.edit_text(
        "📝 Editar Mensagens\n\n"
        "Selecione uma mensagem para editar ou excluir:",
        reply_markup=keyboard
    )
    await callback_query.answer()

async def message_order_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de ordenar mensagens"""
    # Obtém as mensagens configuradas
    messages = await get_welcome_messages(user_bot)
    
    if not messages:
        # Não há mensagens configuradas
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages"))
        
        await callback_query.message.edit_text(
            "❌ Não há mensagens configuradas.",
            reply_markup=keyboard
        )
        await callback_query.answer()
        return
    
    # Cria teclado com as mensagens e botões de ordenação
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    
    for i, msg in enumerate(messages):
        msg_type = msg.get("type", "text")
        msg_id = msg.get("id", "")
        
        # Botões de navegação
        buttons = []
        if i > 0:  # Pode subir
            buttons.append(types.InlineKeyboardButton(
                text="⬆️",
                callback_data=f"move_message_up:{msg_id}"
            ))
        else:
            buttons.append(types.InlineKeyboardButton(
                text=" ",
                callback_data="noop"
            ))
        
        # Rótulo da mensagem
        if msg_type == "text":
            text = msg.get("text", "")
            if len(text) > 20:
                text = text[:20] + "..."
            label = f"{i+1}. texto: {text}"
        else:
            label = f"{i+1}. foto + texto"
        
        buttons.append(types.InlineKeyboardButton(
            text=label,
            callback_data=f"noop"
        ))
        
        if i < len(messages) - 1:  # Pode descer
            buttons.append(types.InlineKeyboardButton(
                text="⬇️",
                callback_data=f"move_message_down:{msg_id}"
            ))
        else:
            buttons.append(types.InlineKeyboardButton(
                text=" ",
                callback_data="noop"
            ))
        
        keyboard.row(*buttons)
    
    # Adiciona botão para voltar
    keyboard.add(types.InlineKeyboardButton(
        text="🔙 Voltar",
        callback_data="config_messages"
    ))
    
    await callback_query.message.edit_text(
        "⚡️ Ordenar Mensagens\n\n"
        "Use as setas ⬆️ ⬇️ para reordenar as mensagens.\n"
        "A ordem definida será a mesma usada ao enviar as mensagens aos usuários.",
        reply_markup=keyboard
    )
    await callback_query.answer()

# Handlers para configuração da PushinPay

async def config_pushinpay_callback(callback_query: types.CallbackQuery, state: FSMContext, user_bot: UserBot):
    """Handler para o callback de configuração da PushinPay"""
    # Verifica se já há token configurado
    current_token = await get_pushinpay_token(user_bot)
    
    if current_token:
        # Já há token configurado
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(text="🔄 Atualizar token", callback_data="update_pushinpay"),
            types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
        )
        
        await callback_query.message.edit_text(
            "💰 CONFIGURAR PUSHINPAY\n\n"
            "✅ Token configurado!\n\n"
            "Seu token da PushinPay está configurado e pronto para receber pagamentos.",
            reply_markup=keyboard
        )
    else:
        # Não há token configurado
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin"))
        
        await callback_query.message.edit_text(
            "💰 CONFIGURAR PUSHINPAY\n\n"
            "Configure seu token da PushinPay para receber pagamentos via PIX.\n\n"
            "Nenhum token configurado.\n\n"
            "Envie seu token da PushinPay ou clique em 'Voltar' para cancelar.",
            reply_markup=keyboard
        )
        
        # Define o estado para aguardar o token
        await BotStates.waiting_pushinpay_token.set()
    
    await callback_query.answer()

async def pushinpay_token_handler(message: types.Message, state: FSMContext, user_bot: UserBot):
    """Handler para receber o token da PushinPay"""
    token = message.text.strip()
    
    # Salva o token
    success = await save_pushinpay_token(user_bot, token)
    
    if success:
        # Notifica sucesso
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(text="📝 Configurar mensagens", callback_data="config_messages"),
            types.InlineKeyboardButton(text="💰 Integrar Pushin Pay", callback_data="config_pushinpay")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="👥 Adicionar canal/grupo", callback_data="config_chat"),
            types.InlineKeyboardButton(text="📞 Configurar suporte", callback_data="config_support")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="📊 Métricas de Vendas", callback_data="sales_metrics"),
            types.InlineKeyboardButton(text="🛍 Adicionar Upsell", callback_data="config_upsell")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="💱 Adicionar Order Bump", callback_data="config_order_bump"),
            types.InlineKeyboardButton(text="📤 Remarketing", callback_data="config_remarketing")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="🎯 Criar planos", callback_data="config_plans")
        )
        
        await message.answer(
            "✅ TOKEN CONFIGURADO!\n\n"
            "Seu token da PushinPay foi configurado com sucesso. "
            "Agora você pode receber pagamentos via PIX.",
            reply_markup=keyboard
        )
        
        # Reseta o estado
        await state.finish()
    else:
        # Notifica erro
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_pushinpay"))
        
        await message.answer(
            "❌ Erro ao salvar o token.\n\n"
            "Por favor, verifique se o token está correto e tente novamente.",
            reply_markup=keyboard
        )

# Handlers para configuração de chat VIP

async def config_chat_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de configuração de chat VIP"""
    # Obtém a configuração atual do chat
    chat_config = await user_bot.get_chat_config()
    
    # Prepara o texto da mensagem
    text = build_channel_info_text(chat_config)
    
    # Adiciona instruções
    text += "\n\n💡 Instruções:\n"
    text += "1. Adicione o bot ao grupo/canal\n"
    text += "2. Promova o bot para administrador com todas as permissões\n"
    text += "3. Use @GetMy_IdBot para obter o ID correto\n"
    text += "4. Configure o ID aqui\n\n"
    
    text += "⚠️ Importante:\n"
    text += "• O chat deve ser um supergrupo ou canal\n"
    text += "• O ID deve começar com -100\n"
    text += "• O bot precisa ser administrador\n"
    text += "• Todas as permissões necessárias devem estar ativadas"
    
    # Cria teclado com opções
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="➕ Configurar chat VIP", callback_data="set_chat"),
        types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
    )
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()

async def set_chat_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de configurar chat VIP"""
    # Solicita o ID do chat
    text = (
        "👥 Digite o ID do chat VIP:\n\n"
        "ℹ️ O bot precisa ser administrador do chat com permissões para:\n"
        "• Gerar links de convite\n"
        "• Gerenciar usuários\n"
        "• Enviar mensagens"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🔙 Cancelar", callback_data="config_chat"))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    # Define o estado para aguardar o ID do chat
    await BotStates.waiting_chat_id.set()
    
    await callback_query.answer()

async def chat_id_handler(message: types.Message, state: FSMContext, user_bot: UserBot):
    """Handler para receber o ID do chat VIP"""
    try:
        chat_id = message.text.strip()
        
        # Verifica se o ID está no formato correto
        if not (chat_id.startswith('-100') and chat_id[4:].isdigit()):
            raise ValueError("ID inválido")
        
        # Tenta obter informações do chat
        chat = await user_bot.bot.get_chat(chat_id)
        
        # Verifica se o bot é administrador
        bot_member = await chat.get_member(user_bot.bot.id)
        is_admin = bot_member.is_chat_admin()
        
        if not is_admin:
            await message.answer(
                "❌ O bot não é administrador do chat.\n\n"
                "Por favor, promova o bot para administrador e tente novamente."
            )
            return
        
        # Salva a configuração do chat
        chat_config = {
            "chat_id": chat_id,
            "chat_title": chat.title,
            "chat_type": chat.type,
            "chat_username": chat.username
        }
        
        success = await user_bot.save_chat_config(chat_config)
        
        if success:
            # Notifica sucesso
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_chat"))
            
            await message.answer(
                f"✅ Chat VIP configurado com sucesso!\n\n"
                f"Chat: {chat.title}\n"
                f"ID: {chat_id}",
                reply_markup=keyboard
            )
            
            # Reseta o estado
            await state.finish()
        else:
            # Notifica erro
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_chat"))
            
            await message.answer(
                "❌ Erro ao salvar a configuração do chat.\n\n"
                "Por favor, tente novamente.",
                reply_markup=keyboard
            )
    except ValueError:
        # ID inválido
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_chat"))
        
        await message.answer(
            "❌ ID inválido.\n\n"
            "O ID deve começar com -100 seguido de dígitos.",
            reply_markup=keyboard
        )
    except Exception as e:
        # Erro ao obter informações do chat
        logger.error(f"Erro ao verificar chat: {e}", exc_info=True)
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_chat"))
        
        await message.answer(
            "❌ Erro ao verificar o chat.\n\n"
            "Verifique se o ID está correto e se o bot foi adicionado ao chat.",
            reply_markup=keyboard
        )

# Handlers para configuração de suporte

async def config_support_callback(callback_query: types.CallbackQuery, state: FSMContext, user_bot: UserBot):
    """Handler para o callback de configuração de suporte"""
    # Obtém a configuração atual de suporte
    support_config = await get_support_config(user_bot)
    
    if support_config and "username" in support_config:
        # Já há usuário configurado
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(text="🔄 Atualizar usuário", callback_data="update_support"),
            types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
        )
        
        await callback_query.message.edit_text(
            f"📱 CONFIGURAR USUÁRIO DE SUPORTE\n\n"
            f"Usuário de suporte atual: @{support_config['username']}\n\n"
            f"Este usuário será exibido quando os usuários utilizarem o comando /suporte.",
            reply_markup=keyboard
        )
    else:
        # Não há usuário configurado
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin"))
        
        await callback_query.message.edit_text(
            "📱 CONFIGURAR USUÁRIO DE SUPORTE\n\n"
            "Usuário de suporte atual: Não configurado\n\n"
            "Envie o nome de usuário (sem @) que será exibido quando os usuários "
            "utilizarem o comando /suporte:",
            reply_markup=keyboard
        )
        
        # Define o estado para aguardar o username
        await BotStates.waiting_support_username.set()
    
    await callback_query.answer()

async def update_support_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de atualizar usuário de suporte"""
    # Solicita o novo username
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🔙 Cancelar", callback_data="config_support"))
    
    await callback_query.message.edit_text(
        "📱 ATUALIZAR USUÁRIO DE SUPORTE\n\n"
        "Envie o novo nome de usuário (sem @) que será exibido quando os usuários "
        "utilizarem o comando /suporte:",
        reply_markup=keyboard
    )
    
    # Define o estado para aguardar o username
    await BotStates.waiting_support_username.set()
    
    await callback_query.answer()

async def support_username_handler(message: types.Message, state: FSMContext, user_bot: UserBot):
    """Handler para receber o username de suporte"""
    username = message.text.strip()
    
    # Remove @ se estiver presente
    if username.startswith('@'):
        username = username[1:]
    
    # Salva a configuração de suporte
    support_config = {"username": username}
    success = await save_support_config(user_bot, support_config)
    
    if success:
        # Notifica sucesso
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin"))
        
        await message.answer(
            f"✅ Usuário de suporte configurado com sucesso!\n\n"
            f"Agora os usuários serão direcionados para @{username} quando "
            f"utilizarem o comando /suporte.",
            reply_markup=keyboard
        )
        
        # Reseta o estado
        await state.finish()
    else:
        # Notifica erro
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_support"))
        
        await message.answer(
            "❌ Erro ao salvar a configuração de suporte.\n\n"
            "Por favor, tente novamente.",
            reply_markup=keyboard
        )

# Handlers para visualização de métricas

async def sales_metrics_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de métricas de vendas"""
    # Cria teclado com opções de período
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="📅 7 Dias", callback_data="metrics:7_days"),
        types.InlineKeyboardButton(text="📆 15 Dias", callback_data="metrics:15_days")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="📈 30 Dias", callback_data="metrics:30_days"),
        types.InlineKeyboardButton(text="📊 3 meses", callback_data="metrics:3_months")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="🗓 6 meses", callback_data="metrics:6_months"),
        types.InlineKeyboardButton(text="🚀 1 ano", callback_data="metrics:1_year")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="🧭 Todo período", callback_data="metrics:all_time")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
    )
    
    await callback_query.message.edit_text(
        "📊 MÉTRICAS DE VENDAS\n\n"
        "Selecione um período para visualizar as estatísticas:",
        reply_markup=keyboard
    )
    
    await callback_query.answer()

async def metrics_period_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de período de métricas"""
    period = callback_query.data.split(':')[1]
    
    # Obtém as métricas para o período
    metrics = await get_sales_metrics(user_bot, period)
    
    # Formata os valores
    total_sales = format_price(metrics.get("total_sales", 0))
    sales_count = metrics.get("sales_count", 0)
    commission = format_price(metrics.get("commission", 0))
    total_users = metrics.get("total_users", 0)
    paying_users = metrics.get("paying_users", 0)
    
    # Formata o período para exibição
    period_text = "Últimos 7 dias"
    if period == "15_days":
        period_text = "Últimos 15 dias"
    elif period == "30_days":
        period_text = "Últimos 30 dias"
    elif period == "3_months":
        period_text = "Últimos 3 meses"
    elif period == "6_months":
        period_text = "Últimos 6 meses"
    elif period == "1_year":
        period_text = "Último ano"
    elif period == "all_time":
        period_text = "Todo o período"
    
    # Prepara o texto da mensagem
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    text = (
        f"📊 Estatísticas do Bot\n\n"
        f"📅 Período: {period_text}\n"
        f"💰 Total de vendas: {total_sales}\n"
        f"🛒 Quantidade de vendas: {sales_count}\n"
        f"💸 Comissão estimada (20%): {commission}\n"
        f"👥 Total de usuários: {total_users}\n"
        f"✅ Usuários pagantes: {paying_users}\n"
        f"⏱️ Data/Hora: {now}"
    )
    
    # Cria teclado para voltar
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="sales_metrics"))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()

# Handlers para configuração de planos

async def config_plans_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de configuração de planos"""
    # Obtém os planos configurados
    plans = await get_plans(user_bot)
    
    # Prepara o texto da mensagem
    if plans:
        text = "💰 CONFIGURAR PLANOS\n\n"
        for plan in plans:
            plan_info = format_plan_info(plan)
            text += f"{plan_info}\n\n"
    else:
        text = (
            "💰 CONFIGURAR PLANOS\n\n"
            "Nenhum plano configurado.\n\n"
            "Clique em 'Adicionar plano' para criar um novo plano."
        )
    
    # Cria teclado com opções
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="➕ Adicionar plano", callback_data="add_plan"),
        types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
    )
    
    # Se houver planos, adiciona a opção para visualizar completo
    if plans:
        keyboard.add(types.InlineKeyboardButton(
            text="👀 Visualização completa",
            callback_data="view_plans_complete"
        ))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()

async def add_plan_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de adicionar plano"""
    # Solicita o nome do plano
    text = "💰 ADICIONAR PLANO\n\nEnvie o nome do plano que será exibido no botão:"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_plans"))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    # Define o estado para aguardar o nome do plano
    await BotStates.waiting_plan_name.set()
    
    await callback_query.answer()

async def plan_name_handler(message: types.Message, state: FSMContext):
    """Handler para receber o nome do plano"""
    plan_name = message.text.strip()
    
    # Salva o nome no estado
    await state.update_data(plan_name=plan_name)
    
    # Solicita o preço do plano
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_plans"))
    
    await message.answer(
        f"✅ NOME RECEBIDO!\n"
        f"Nome do plano: {plan_name}\n\n"
        f"Agora, envie o valor do plano (ex: 19.90):",
        reply_markup=keyboard
    )
    
    # Atualiza o estado para aguardar o preço
    await BotStates.waiting_plan_price.set()

async def plan_price_handler(message: types.Message, state: FSMContext):
    """Handler para receber o preço do plano"""
    try:
        # Tenta converter para float
        plan_price = float(message.text.strip().replace(',', '.'))
        
        # Salva o preço no estado
        await state.update_data(plan_price=plan_price)
        
        # Obtém o nome do plano do estado
        data = await state.get_data()
        plan_name = data.get("plan_name", "")
        
        # Solicita a duração do plano
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(text="1 Dia", callback_data="plan_duration:1_day"),
            types.InlineKeyboardButton(text="7 Dias", callback_data="plan_duration:7_days")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="15 Dias", callback_data="plan_duration:15_days"),
            types.InlineKeyboardButton(text="30 Dias", callback_data="plan_duration:30_days")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="3 Meses", callback_data="plan_duration:3_months"),
            types.InlineKeyboardButton(text="6 Meses", callback_data="plan_duration:6_months")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="1 Ano", callback_data="plan_duration:1_year"),
            types.InlineKeyboardButton(text="Vitalício", callback_data="plan_duration:lifetime")
        )
        
        await message.answer(
            f"✅ PREÇO RECEBIDO!\n"
            f"Preço do plano: R$ {plan_price:.2f}\n\n"
            f"Agora, selecione a duração do plano:",
            reply_markup=keyboard
        )
    except ValueError:
        # Preço inválido
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_plans"))
        
        await message.answer(
            "❌ Valor inválido.\n\n"
            "Por favor, envie um número válido (ex: 19.90):",
            reply_markup=keyboard
        )
        
        # Mantém o estado para aguardar um novo preço
        await BotStates.waiting_plan_price.set()

async def plan_duration_callback(callback_query: types.CallbackQuery, state: FSMContext, user_bot: UserBot):
    """Handler para o callback de duração do plano"""
    duration = callback_query.data.split(':')[1]
    
    # Obtém dados do estado
    data = await state.get_data()
    plan_name = data.get("plan_name", "")
    plan_price = data.get("plan_price", 0)
    
    # Formato de exibição da duração
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
    
    # Cria plano
    plan_data = {
        "name": plan_name,
        "price": plan_price,
        "duration": duration
    }
    
    # Salva o plano
    success = await save_plan(user_bot, plan_data)
    
    if success:
        # Notifica sucesso
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(text="➕ Adicionar outro plano", callback_data="add_plan"),
            types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_plans")
        )
        
        await callback_query.message.edit_text(
            f"✅ PLANO ADICIONADO!\n\n"
            f"• Nome: {plan_name}\n"
            f"• Preço: R$ {plan_price:.2f}\n"
            f"• Duração: {duration_text}\n\n"
            f"O plano foi adicionado com sucesso e já está disponível para os usuários.",
            reply_markup=keyboard
        )
        
        # Reseta o estado
        await state.finish()
    else:
        # Notifica erro
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_plans"))
        
        await callback_query.message.edit_text(
            "❌ Erro ao salvar o plano.\n\n"
            "Por favor, tente novamente.",
            reply_markup=keyboard
        )
    
    await callback_query.answer()

async def view_plans_complete_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de visualização completa dos planos"""
    # Obtém os planos configurados
    plans = await get_plans(user_bot)
    
    if not plans:
        # Não há planos configurados
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_plans"))
        
        await callback_query.message.edit_text(
            "❌ Não há planos configurados.",
            reply_markup=keyboard
        )
        await callback_query.answer()
        return
    
    # Cria preview das mensagens de boas-vindas
    welcome_messages = await get_welcome_messages(user_bot)
    
    # Envia as mensagens em sequência
    await callback_query.answer("Enviando visualização completa...")
    
    # Primeiro envia as mensagens de boas-vindas
    for msg in welcome_messages:
        msg_type = msg.get("type", "text")
        
        if msg_type == "text":
            await callback_query.message.answer(msg.get("text", ""), parse_mode="HTML")
        elif msg_type == "media" or msg_type == "media_with_text":
            media_id = msg.get("media_id")
            caption = msg.get("text", "")
            
            if media_id:
                try:
                    # Determina o tipo de mídia
                    if msg.get("media_type") == "photo":
                        await callback_query.message.answer_photo(media_id, caption=caption, parse_mode="HTML")
                    elif msg.get("media_type") == "video":
                        await callback_query.message.answer_video(media_id, caption=caption, parse_mode="HTML")
                    elif msg.get("media_type") == "animation":
                        await callback_query.message.answer_animation(media_id, caption=caption, parse_mode="HTML")
                    else:
                        # Fallback para documentos
                        await callback_query.message.answer_document(media_id, caption=caption, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Erro ao enviar mídia: {e}", exc_info=True)
                    await callback_query.message.answer(caption, parse_mode="HTML")
    
    # Cria teclado com os planos
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    for plan in plans:
        plan_name = plan.get("name", "Plano")
        plan_price = plan.get("price", 0)
        plan_id = plan.get("id", "")
        
        keyboard.add(types.InlineKeyboardButton(
            text=f"{plan_name} - {format_price(plan_price)}",
            callback_data=f"plan:{plan_id}"
        ))
    
    # Verifica se há order bump configurado
    order_bump = await get_order_bump_config(user_bot)
    if order_bump and order_bump.get("active", False):
        # Adiciona botão de order bump
        keyboard.add(types.InlineKeyboardButton(
            text=f"{order_bump.get('text', 'Order Bump')} - {format_price(order_bump.get('price', 0))}",
            callback_data="order_bump"
        ))
    
    # Botão para voltar
    keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_plans"))
    
    # Envia mensagem com os planos
    await callback_query.message.answer(
        "🛒 <b>Planos Disponíveis</b>\n\n"
        "Selecione um plano para assinar:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Handlers para configuração de upsell

async def config_upsell_callback(callback_query: types.CallbackQuery, state: FSMContext, user_bot: UserBot):
    """Handler para o callback de configuração de upsell"""
    # Obtém a configuração atual de upsell
    upsell_config = await get_upsell_config(user_bot)
    
    if upsell_config:
        # Já há configuração de upsell
        is_active = upsell_config.get("active", False)
        status_text = "✅ Ativo" if is_active else "❌ Inativo"
        
        text = (
            "🔔 UPSELL CONFIGURADO\n\n"
            f"Texto: {upsell_config.get('text', '')}\n"
            f"Botão: {upsell_config.get('button_text', '')}\n"
            f"Preço: R$ {upsell_config.get('price', 0):.2f}\n"
            f"Link: {upsell_config.get('link', '')}\n"
            f"Status: {status_text}\n\n"
            "Selecione uma opção:"
        )
        
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(text="📝 Editar upsell", callback_data="edit_upsell"),
            types.InlineKeyboardButton(
                text="🔴 Desativar" if is_active else "🟢 Ativar",
                callback_data="toggle_upsell"
            ),
            types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
        )
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    else:
        # Não há configuração de upsell
        text = (
            "🔔 CONFIGURAR UPSELL\n\n"
            "Envie o texto da oferta complementar que será exibida 3 minutos após a compra:"
        )
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="back_to_admin"))
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        
        # Define o estado para aguardar o texto do upsell
        await BotStates.waiting_upsell_text.set()
    
    await callback_query.answer()

async def edit_upsell_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de editar upsell"""
    # Solicita o texto do upsell
    text = (
        "🔔 EDITAR UPSELL\n\n"
        "Envie o novo texto da oferta complementar que será exibida 3 minutos após a compra:"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_upsell"))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    # Define o estado para aguardar o texto do upsell
    await BotStates.waiting_upsell_text.set()
    
    await callback_query.answer()

async def toggle_upsell_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de ativar/desativar upsell"""
    # Toggle do status do upsell
    success = await toggle_upsell(user_bot)
    
    if success:
        # Notifica sucesso
        upsell_config = await get_upsell_config(user_bot)
        is_active = upsell_config.get("active", False)
        status_text = "ativado" if is_active else "desativado"
        
        await callback_query.answer(f"✅ Upsell {status_text} com sucesso!")
        
        # Atualiza a mensagem
        callback_query.data = "config_upsell"
        await config_upsell_callback(callback_query, None, user_bot)
    else:
        # Notifica erro
        await callback_query.answer("❌ Erro ao alterar status do upsell.")

async def upsell_text_handler(message: types.Message, state: FSMContext):
    """Handler para receber o texto do upsell"""
    upsell_text = message.text.strip()
    
    # Salva o texto no estado
    await state.update_data(upsell_text=upsell_text)
    
    # Solicita o texto do botão
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_upsell"))
    
    await message.answer(
        "✅ TEXTO RECEBIDO!\n\n"
        "Agora, envie o texto que será exibido no botão da oferta complementar:",
        reply_markup=keyboard
    )
    
    # Atualiza o estado para aguardar o texto do botão
    await BotStates.waiting_upsell_button_text.set()

async def upsell_button_text_handler(message: types.Message, state: FSMContext):
    """Handler para receber o texto do botão do upsell"""
    button_text = message.text.strip()
    
    # Salva o texto do botão no estado
    await state.update_data(upsell_button_text=button_text)
    
    # Solicita o preço do upsell
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_upsell"))
    
    await message.answer(
        "✅ TEXTO DO BOTÃO RECEBIDO!\n\n"
        "Agora, envie o valor da oferta complementar (ex: 19.90):",
        reply_markup=keyboard
    )
    
    # Atualiza o estado para aguardar o preço
    await BotStates.waiting_upsell_price.set()

async def upsell_price_handler(message: types.Message, state: FSMContext):
    """Handler para receber o preço do upsell"""
    try:
        # Tenta converter para float
        price = float(message.text.strip().replace(',', '.'))
        
        # Salva o preço no estado
        await state.update_data(upsell_price=price)
        
        # Solicita o link do upsell
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_upsell"))
        
        await message.answer(
            "✅ PREÇO RECEBIDO!\n\n"
            "Por fim, envie o link que o usuário receberá após o pagamento da oferta complementar:",
            reply_markup=keyboard
        )
        
        # Atualiza o estado para aguardar o link
        await BotStates.waiting_upsell_link.set()
    except ValueError:
        # Preço inválido
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_upsell"))
        
        await message.answer(
            "❌ Valor inválido.\n\n"
            "Por favor, envie um número válido (ex: 19.90):",
            reply_markup=keyboard
        )
        
        # Mantém o estado para aguardar um novo preço
        await BotStates.waiting_upsell_price.set()

async def upsell_link_handler(message: types.Message, state: FSMContext, user_bot: UserBot):
    """Handler para receber o link do upsell"""
    link = message.text.strip()
    
    # Obtém dados do estado
    data = await state.get_data()
    upsell_text = data.get("upsell_text", "")
    button_text = data.get("upsell_button_text", "")
    price = data.get("upsell_price", 0)
    
    # Cria configuração de upsell
    upsell_config = {
        "text": upsell_text,
        "button_text": button_text,
        "price": price,
        "link": link,
        "active": True
    }
    
    # Salva a configuração
    success = await save_upsell_config(user_bot, upsell_config)
    
    if success:
        # Notifica sucesso
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin"))
        
        await message.answer(
            "✅ UPSELL CONFIGURADO COM SUCESSO!\n\n"
            f"Texto: {upsell_text}\n"
            f"Botão: {button_text}\n"
            f"Preço: R$ {price:.2f}\n"
            f"Link: {link}\n\n"
            "A oferta complementar será exibida 3 minutos após a compra de um plano.",
            reply_markup=keyboard
        )
        
        # Reseta o estado
        await state.finish()
    else:
        # Notifica erro
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_upsell"))
        
        await message.answer(
            "❌ Erro ao salvar a configuração de upsell.\n\n"
            "Por favor, tente novamente.",
            reply_markup=keyboard
        )

# Handlers para configuração de order bump

async def config_order_bump_callback(callback_query: types.CallbackQuery, state: FSMContext, user_bot: UserBot):
    """Handler para o callback de configuração de order bump"""
    # Obtém a configuração atual de order bump
    order_bump_config = await get_order_bump_config(user_bot)
    
    if order_bump_config:
        # Já há configuração de order bump
        is_active = order_bump_config.get("active", False)
        status_text = "✅ Ativo" if is_active else "❌ Inativo"
        
        text = (
            "🔔 ORDER BUMP CONFIGURADO\n\n"
            f"Texto: {order_bump_config.get('text', '')}\n"
            f"Preço: R$ {order_bump_config.get('price', 0):.2f}\n"
            f"Link: {order_bump_config.get('link', '')}\n"
            f"Status: {status_text}\n\n"
            "Selecione uma opção:"
        )
        
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(text="📝 Editar Order Bump", callback_data="edit_order_bump"),
            types.InlineKeyboardButton(
                text="🔴 Desativar" if is_active else "🟢 Ativar",
                callback_data="toggle_order_bump"
            ),
            types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
        )
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    else:
        # Não há configuração de order bump
        text = (
            "🔔 CONFIGURAR ORDER BUMP\n\n"
            "Envie o texto que será exibido no botão da oferta complementar:"
        )
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="back_to_admin"))
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        
        # Define o estado para aguardar o texto do order bump
        await BotStates.waiting_order_bump_text.set()
    
    await callback_query.answer()

async def edit_order_bump_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de editar order bump"""
    # Solicita o texto do order bump
    text = (
        "🔔 EDITAR ORDER BUMP\n\n"
        "Envie o novo texto que será exibido no botão da oferta complementar:"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_order_bump"))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    # Define o estado para aguardar o texto do order bump
    await BotStates.waiting_order_bump_text.set()
    
    await callback_query.answer()

async def toggle_order_bump_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de ativar/desativar order bump"""
    # Toggle do status do order bump
    success = await toggle_order_bump(user_bot)
    
    if success:
        # Notifica sucesso
        order_bump_config = await get_order_bump_config(user_bot)
        is_active = order_bump_config.get("active", False)
        status_text = "ativado" if is_active else "desativado"
        
        await callback_query.answer(f"✅ Order Bump {status_text} com sucesso!")
        
        # Atualiza a mensagem
        callback_query.data = "config_order_bump"
        await config_order_bump_callback(callback_query, None, user_bot)
    else:
        # Notifica erro
        await callback_query.answer("❌ Erro ao alterar status do Order Bump.")

async def order_bump_text_handler(message: types.Message, state: FSMContext):
    """Handler para receber o texto do order bump"""
    text = message.text.strip()
    
    # Salva o texto no estado
    await state.update_data(order_bump_text=text)
    
    # Solicita o preço do order bump
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_order_bump"))
    
    await message.answer(
        "✅ TEXTO DO BOTÃO RECEBIDO!\n\n"
        "Agora, envie o valor da oferta complementar (ex: 19.90):",
        reply_markup=keyboard
    )
    
    # Atualiza o estado para aguardar o preço
    await BotStates.waiting_order_bump_price.set()

async def order_bump_price_handler(message: types.Message, state: FSMContext):
    """Handler para receber o preço do order bump"""
    try:
        # Tenta converter para float
        price = float(message.text.strip().replace(',', '.'))
        
        # Salva o preço no estado
        await state.update_data(order_bump_price=price)
        
        # Solicita o link do order bump
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_order_bump"))
        
        await message.answer(
            "✅ PREÇO RECEBIDO!\n\n"
            "Por fim, envie o link que o usuário receberá após o pagamento da oferta complementar:",
            reply_markup=keyboard
        )
        
        # Atualiza o estado para aguardar o link
        await BotStates.waiting_order_bump_link.set()
    except ValueError:
        # Preço inválido
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_order_bump"))
        
        await message.answer(
            "❌ Valor inválido.\n\n"
            "Por favor, envie um número válido (ex: 19.90):",
            reply_markup=keyboard
        )
        
        # Mantém o estado para aguardar um novo preço
        await BotStates.waiting_order_bump_price.set()

async def order_bump_link_handler(message: types.Message, state: FSMContext, user_bot: UserBot):
    """Handler para receber o link do order bump"""
    link = message.text.strip()
    
    # Obtém dados do estado
    data = await state.get_data()
    text = data.get("order_bump_text", "")
    price = data.get("order_bump_price", 0)
    
    # Cria configuração de order bump
    order_bump_config = {
        "text": text,
        "price": price,
        "link": link,
        "active": True
    }
    
    # Salva a configuração
    success = await save_order_bump_config(user_bot, order_bump_config)
    
    if success:
        # Notifica sucesso
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin"))
        
        await message.answer(
            "✅ ORDER BUMP CONFIGURADO COM SUCESSO!\n\n"
            f"Texto: {text}\n"
            f"Preço: R$ {price:.2f}\n"
            f"Link: {link}\n\n"
            "A oferta complementar será exibida junto com os planos.",
            reply_markup=keyboard
        )
        
        # Reseta o estado
        await state.finish()
    else:
        # Notifica erro
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_order_bump"))
        
        await message.answer(
            "❌ Erro ao salvar a configuração de Order Bump.\n\n"
            "Por favor, tente novamente.",
            reply_markup=keyboard
        )

# Handlers para remarketing

async def config_remarketing_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de configuração de remarketing"""
    # Solicita o público-alvo
    text = (
        "🔄 Remarketing Personalizado\n\n"
        "Selecione o público-alvo para a mensagem:"
    )
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="👤 Somente não pagantes", callback_data="remarketing_target:non_paying"),
        types.InlineKeyboardButton(text="👥 Todos os usuários", callback_data="remarketing_target:all"),
        types.InlineKeyboardButton(text="🔙 Voltar ao menu", callback_data="back_to_admin")
    )
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()

async def remarketing_target_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de público-alvo do remarketing"""
    target = callback_query.data.split(':')[1]
    
    # Salva o público-alvo no estado
    await state.update_data(remarketing_target=target)
    
    # Solicita se deseja incluir promoção
    text = "Deseja incluir uma promoção na mensagem de remarketing?"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="SIM", callback_data="remarketing_promotion:yes"),
        types.InlineKeyboardButton(text="NÃO", callback_data="remarketing_promotion:no")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_remarketing")
    )
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()

async def remarketing_promotion_callback(callback_query: types.CallbackQuery, state: FSMContext, user_bot: UserBot):
    """Handler para o callback de promoção do remarketing"""
    include_promotion = callback_query.data.split(':')[1] == "yes"
    
    # Salva a opção de promoção no estado
    await state.update_data(include_promotion=include_promotion)
    
    if include_promotion:
        # Obtém os planos disponíveis
        plans = await get_plans(user_bot)
        
        if not plans:
            # Não há planos configurados
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="config_remarketing"))
            
            await callback_query.message.edit_text(
                "❌ Não há planos configurados para criar uma promoção.\n\n"
                "Configure pelo menos um plano antes de criar uma promoção.",
                reply_markup=keyboard
            )
            await callback_query.answer()
            return
        
        # Cria teclado com os planos disponíveis
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        for plan in plans:
            plan_name = plan.get("name", "Plano")
            plan_price = plan.get("price", 0)
            plan_id = plan.get("id", "")
            
            keyboard.add(types.InlineKeyboardButton(
                text=f"{plan_name} - R$ {plan_price:.2f}",
                callback_data=f"remarketing_plan:{plan_id}"
            ))
        
        # Adiciona opção de plano personalizado
        keyboard.add(types.InlineKeyboardButton(
            text="Personalizado",
            callback_data="remarketing_plan:custom"
        ))
        
        # Botão para cancelar
        keyboard.add(types.InlineKeyboardButton(
            text="❌ Cancelar",
            callback_data="config_remarketing"
        ))
        
        await callback_query.message.edit_text(
            "Selecione o plano para a promoção:",
            reply_markup=keyboard
        )
    else:
        # Solicita a mensagem de remarketing
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_remarketing"))
        
        await callback_query.message.edit_text(
            "Envie a mensagem de remarketing que deseja enviar aos usuários.\n\n"
            "Você pode enviar texto, imagens, vídeos ou áudios. Para enviar o conteúdo, "
            "basta enviar normalmente como uma mensagem no chat.\n\n"
            "Para cancelar, digite /cancel",
            reply_markup=keyboard
        )
        
        # Define o estado para aguardar a mensagem
        await BotStates.waiting_remarketing_message.set()
    
    await callback_query.answer()

async def remarketing_price_handler(message: types.Message, state: FSMContext):
    """Handler para receber o preço promocional do remarketing"""
    try:
        # Tenta converter para float
        price = float(message.text.strip().replace(',', '.'))
        
        # Salva o preço no estado
        await state.update_data(remarketing_price=price)
        
        # Solicita a mensagem de remarketing
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_remarketing"))
        
        await message.answer(
            f"Valor da promoção salvo com sucesso: R$ {price:.2f}\n\n"
            "Envie-me a mensagem que gostaria de enviar junto com a promoção.\n"
            "Obs: faça uma mensagem única.\n"
            "Você pode enviar texto, imagens, vídeos ou áudios.",
            reply_markup=keyboard
        )
        
        # Atualiza o estado para aguardar a mensagem
        await BotStates.waiting_remarketing_message.set()
    except ValueError:
        # Preço inválido
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_remarketing"))
        
        await message.answer(
            "❌ Valor inválido.\n\n"
            "Por favor, envie um número válido (ex: 19.90):",
            reply_markup=keyboard
        )
        
        # Mantém o estado para aguardar um novo preço
        await BotStates.waiting_remarketing_price.set()

async def remarketing_message_handler(message: types.Message, state: FSMContext, user_bot: UserBot):
    """Handler para receber a mensagem de remarketing"""
    # Obtém dados do estado
    data = await state.get_data()
    target = data.get("remarketing_target", "all")
    include_promotion = data.get("include_promotion", False)
    
    # Prepara a mensagem de remarketing
    message_data = {}
    
    # Verifica o tipo de mensagem
    if message.text:
        message_data["type"] = "text"
        message_data["text"] = message.text
    elif message.photo:
        message_data["type"] = "photo"
        message_data["file_id"] = message.photo[-1].file_id
        message_data["caption"] = message.caption or ""
    elif message.video:
        message_data["type"] = "video"
        message_data["file_id"] = message.video.file_id
        message_data["caption"] = message.caption or ""
    elif message.animation:
        message_data["type"] = "animation"
        message_data["file_id"] = message.animation.file_id
        message_data["caption"] = message.caption or ""
    elif message.voice:
        message_data["type"] = "voice"
        message_data["file_id"] = message.voice.file_id
        message_data["caption"] = message.caption or ""
    elif message.audio:
        message_data["type"] = "audio"
        message_data["file_id"] = message.audio.file_id
        message_data["caption"] = message.caption or ""
    elif message.document:
        message_data["type"] = "document"
        message_data["file_id"] = message.document.file_id
        message_data["caption"] = message.caption or ""
    else:
        # Tipo de mensagem não suportado
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_remarketing"))
        
        await message.answer(
            "❌ Tipo de mensagem não suportado.\n\n"
            "Por favor, envie texto, imagem, vídeo, GIF, voz, áudio ou documento:",
            reply_markup=keyboard
        )
        
        # Mantém o estado para aguardar uma nova mensagem
        return
    
    # Adiciona dados de promoção se necessário
    if include_promotion:
        remarketing_price = data.get("remarketing_price", 0)
        
        if "remarketing_plan_id" in data:
            # Plano existente
            message_data["promotion"] = {
                "plan_id": data.get("remarketing_plan_id"),
                "plan_name": data.get("remarketing_plan_name"),
                "plan_duration": data.get("remarketing_plan_duration"),
                "price": remarketing_price
            }
        else:
            # Plano personalizado
            message_data["promotion"] = {
                "price": remarketing_price,
                "custom": True
            }
    
    # Salva a mensagem no estado
    await state.update_data(remarketing_message=message_data)
    
    # Envia prévia da mensagem
    await message.answer("Salvamos sua mensagem! Veja abaixo como ficará:")
    
    # Cria a prévia
    await prepare_remarketing_message(message, user_bot, message_data)
    
    # Calcula o número de destinatários
    recipients_count = await user_bot.get_users_count(target == "non_paying")
    
    # Cria teclado com opções
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="📤 ENVIAR AGORA", callback_data="send_remarketing"),
        types.InlineKeyboardButton(text="✏️ EDITAR MENSAGEM", callback_data="edit_remarketing"),
        types.InlineKeyboardButton(text="❌ CANCELAR", callback_data="config_remarketing")
    )
    
    # Target text
    target_text = "Somente não pagantes" if target == "non_paying" else "Todos os usuários"
    
    await message.answer(
        "Salvamos sua mensagem! Para finalizar, clique em \"ENVIAR AGORA\" no botão abaixo, "
        "ou \"EDITAR MENSAGEM\".\n\n"
        f"📊 Informações de Envio:\n"
        f"👥 Público-alvo: {target_text}\n"
        f"🔢 Total de destinatários: {recipients_count}",
        reply_markup=keyboard
    )

async def edit_remarketing_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler para o callback de editar mensagem de remarketing"""
    # Solicita a nova mensagem
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="❌ Cancelar", callback_data="config_remarketing"))
    
    await callback_query.message.edit_text(
        "Envie a nova mensagem que gostaria de enviar junto com a promoção.\n"
        "Obs: faça uma mensagem única.\n"
        "Você pode enviar texto, imagens, vídeos ou áudios.",
        reply_markup=keyboard
    )
    
    # Define o estado para aguardar a mensagem
    await BotStates.waiting_remarketing_message.set()
    
    await callback_query.answer()

async def send_remarketing_callback(callback_query: types.CallbackQuery, state: FSMContext, user_bot: UserBot):
    """Handler para o callback de enviar remarketing"""
    # Obtém dados do estado
    data = await state.get_data()
    target = data.get("remarketing_target", "all")
    message_data = data.get("remarketing_message", {})
    
    if not message_data:
        # Não há mensagem para enviar
        await callback_query.answer("❌ Não há mensagem para enviar.")
        return
    
    # Envia a mensagem para os usuários
    sent_count = await send_remarketing_message(user_bot, message_data, target == "non_paying")
    
    # Notifica o resultado
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin"))
    
    await callback_query.message.edit_text(
        f"✅ Remarketing enviado com sucesso!\n\n"
        f"📊 Estatísticas:\n"
        f"👥 Público-alvo: {'Somente não pagantes' if target == 'non_paying' else 'Todos os usuários'}\n"
        f"📤 Mensagens enviadas: {sent_count}",
        reply_markup=keyboard
    )
    
    # Reseta o estado
    await state.finish()
    
    await callback_query.answer()

# Handlers para callback de planos

async def plan_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de seleção de plano"""
    plan_id = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id
    
    # Obtém dados do plano
    plans = await get_plans(user_bot)
    selected_plan = None
    
    for plan in plans:
        if plan.get("id") == plan_id:
            selected_plan = plan
            break
    
    if not selected_plan:
        # Plano não encontrado
        await callback_query.answer("❌ Plano não encontrado.")
        return
    
    # Verifica se há token da PushinPay configurado
    token = await get_pushinpay_token(user_bot)
    
    if not token:
        # Não há token configurado
        await callback_query.answer("❌ Pagamento não configurado pelo administrador.")
        return
    
    # Cria o pagamento
    plan_name = selected_plan.get("name", "Plano")
    plan_price = selected_plan.get("price", 0)
    plan_duration = selected_plan.get("duration", "30_days")
    
    payment_data = {
        "user_id": user_id,
        "plan_id": plan_id,
        "amount": plan_price,
        "duration": plan_duration
    }
    
    payment_result = await create_payment(user_bot, payment_data)
    
    if not payment_result.get("success", False):
        # Erro ao criar pagamento
        await callback_query.answer("❌ Erro ao criar pagamento.")
        return
    
    # Obtém o link de pagamento
    payment_url = payment_result.get("payment_url", "")
    
    if not payment_url:
        # Não há link de pagamento
        await callback_query.answer("❌ Erro ao obter link de pagamento.")
        return
    
    # Cria o teclado com o link de pagamento
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="💰 PAGAR AGORA", url=payment_url),
        types.InlineKeyboardButton(text="🔙 Voltar", callback_data="start")
    )
    
    # Envia a mensagem de pagamento
    await callback_query.message.edit_text(
        f"🛒 Você selecionou o plano *{plan_name}*\n\n"
        f"💰 Valor: R$ {plan_price:.2f}\n"
        f"⏱️ Duração: {format_duration(plan_duration)}\n\n"
        f"Clique no botão abaixo para realizar o pagamento via PIX.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await callback_query.answer()

async def order_bump_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de seleção de order bump"""
    user_id = callback_query.from_user.id
    
    # Obtém dados do order bump
    order_bump = await get_order_bump_config(user_bot)
    
    if not order_bump or not order_bump.get("active", False):
        # Order bump não encontrado ou inativo
        await callback_query.answer("❌ Oferta não disponível.")
        return
    
    # Verifica se há token da PushinPay configurado
    token = await get_pushinpay_token(user_bot)
    
    if not token:
        # Não há token configurado
        await callback_query.answer("❌ Pagamento não configurado pelo administrador.")
        return
    
    # Cria o pagamento
    order_bump_text = order_bump.get("text", "Order Bump")
    order_bump_price = order_bump.get("price", 0)
    order_bump_link = order_bump.get("link", "")
    
    payment_data = {
        "user_id": user_id,
        "amount": order_bump_price,
        "is_order_bump": True,
        "order_bump_link": order_bump_link
    }
    
    payment_result = await create_payment(user_bot, payment_data)
    
    if not payment_result.get("success", False):
        # Erro ao criar pagamento
        await callback_query.answer("❌ Erro ao criar pagamento.")
        return
    
    # Obtém o link de pagamento
    payment_url = payment_result.get("payment_url", "")
    
    if not payment_url:
        # Não há link de pagamento
        await callback_query.answer("❌ Erro ao obter link de pagamento.")
        return
    
    # Cria o teclado com o link de pagamento
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="💰 PAGAR AGORA", url=payment_url),
        types.InlineKeyboardButton(text="🔙 Voltar", callback_data="start")
    )
    
    # Envia a mensagem de pagamento
    await callback_query.message.edit_text(
        f"🛒 Você selecionou a oferta *{order_bump_text}*\n\n"
        f"💰 Valor: R$ {order_bump_price:.2f}\n\n"
        f"Clique no botão abaixo para realizar o pagamento via PIX.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await callback_query.answer()

# Funções auxiliares

def format_duration(duration):
    """Formata a duração para exibição"""
    if duration == "1_day":
        return "1 Dia"
    elif duration == "7_days":
        return "7 Dias"
    elif duration == "15_days":
        return "15 Dias"
    elif duration == "30_days":
        return "30 Dias"
    elif duration == "3_months":
        return "3 Meses"
    elif duration == "6_months":
        return "6 Meses"
    elif duration == "1_year":
        return "1 Ano"
    elif duration == "lifetime":
        return "Vitalício"
    else:
        return "Indefinida"

# Handlers para comandos comuns

async def help_command(message: types.Message, user_bot: UserBot):
    """Handler para o comando /help"""
    # Verifica se é o dono do bot
    user_id = message.from_user.id
    bot_owner_id = user_bot.user_id
    
    if str(user_id) == str(bot_owner_id):
        # Para o dono do bot
        text = (
            "📚 COMANDOS DISPONÍVEIS\n\n"
            "/start - Reinicia o bot e mostra o menu principal\n"
            "/help - Mostra esta mensagem de ajuda\n\n"
            "Para configurar seu bot, use o menu principal."
        )
    else:
        # Para usuários normais
        text = (
            "📚 COMANDOS DISPONÍVEIS\n\n"
            "/start - Reinicia o bot e mostra os planos disponíveis\n"
            "/help - Mostra esta mensagem de ajuda\n"
            "/suporte - Obter suporte"
        )
    
    await message.answer(text)

async def support_command(message: types.Message, user_bot: UserBot):
    """Handler para o comando /suporte"""
    # Obtém configuração de suporte
    support_config = await get_support_config(user_bot)
    
    if support_config and "username" in support_config:
        # Há usuário de suporte configurado
        await message.answer(
            f"📱 SUPORTE\n\n"
            f"Para obter suporte, entre em contato com @{support_config['username']}"
        )
    else:
        # Não há usuário de suporte configurado
        await message.answer(
            "📱 SUPORTE\n\n"
            "O suporte não está configurado para este bot."
        )

# Handlers para utilidades do back-to-menu

async def back_to_admin_callback(callback_query: types.CallbackQuery, user_bot: UserBot):
    """Handler para o callback de voltar ao menu admin"""
    await show_admin_menu(callback_query.message, user_bot)
    await callback_query.answer()

async def noop_callback(callback_query: types.CallbackQuery):
    """Handler para callbacks que não fazem nada"""
    await callback_query.answer()

# Registro de handlers

def register_handlers(dp: Dispatcher):
    """Registra todos os handlers para os bots dos usuários"""
    # Comandos básicos
    dp.register_message_handler(start_command, commands=["start"], state="*")
    dp.register_message_handler(help_command, commands=["help"], state="*")
    dp.register_message_handler(support_command, commands=["suporte"], state="*")
    
    # Callbacks do menu admin
    dp.register_callback_query_handler(back_to_admin_callback, lambda c: c.data == "back_to_admin", state="*")
    dp.register_callback_query_handler(noop_callback, lambda c: c.data == "noop", state="*")
    
    # Handlers para configuração de mensagens
    dp.register_callback_query_handler(config_messages_callback, lambda c: c.data == "config_messages", state="*")
    dp.register_callback_query_handler(new_message_callback, lambda c: c.data == "new_message", state="*")
    dp.register_callback_query_handler(new_text_message_callback, lambda c: c.data == "new_text_message", state="*")
    dp.register_callback_query_handler(new_media_message_callback, lambda c: c.data == "new_media_message", state="*")
    dp.register_message_handler(message_text_handler, state=BotStates.waiting_message_text)
    dp.register_message_handler(message_media_handler, content_types=types.ContentTypes.ANY, state=BotStates.waiting_message_media)
    dp.register_callback_query_handler(view_messages_callback, lambda c: c.data == "view_messages", state="*")
    dp.register_callback_query_handler(edit_messages_callback, lambda c: c.data == "edit_messages", state="*")
    dp.register_callback_query_handler(message_order_callback, lambda c: c.data == "message_order", state="*")
    
    # Handlers para configuração da PushinPay
    dp.register_callback_query_handler(config_pushinpay_callback, lambda c: c.data == "config_pushinpay", state="*")
    dp.register_callback_query_handler(config_pushinpay_callback, lambda c: c.data == "update_pushinpay", state="*")
    dp.register_message_handler(pushinpay_token_handler, state=BotStates.waiting_pushinpay_token)
    
    # Handlers para configuração de chat VIP
    dp.register_callback_query_handler(config_chat_callback, lambda c: c.data == "config_chat", state="*")
    dp.register_callback_query_handler(set_chat_callback, lambda c: c.data == "set_chat", state="*")
    dp.register_message_handler(chat_id_handler, state=BotStates.waiting_chat_id)
    
    # Handlers para configuração de suporte
    dp.register_callback_query_handler(config_support_callback, lambda c: c.data == "config_support", state="*")
    dp.register_callback_query_handler(update_support_callback, lambda c: c.data == "update_support", state="*")
    dp.register_message_handler(support_username_handler, state=BotStates.waiting_support_username)
    
    # Handlers para visualização de métricas
    dp.register_callback_query_handler(sales_metrics_callback, lambda c: c.data == "sales_metrics", state="*")
    dp.register_callback_query_handler(metrics_period_callback, lambda c: c.data.startswith("metrics:"), state="*")
    
    # Handlers para configuração de planos
    dp.register_callback_query_handler(config_plans_callback, lambda c: c.data == "config_plans", state="*")
    dp.register_callback_query_handler(add_plan_callback, lambda c: c.data == "add_plan", state="*")
    dp.register_message_handler(plan_name_handler, state=BotStates.waiting_plan_name)
    dp.register_message_handler(plan_price_handler, state=BotStates.waiting_plan_price)
    dp.register_callback_query_handler(plan_duration_callback, lambda c: c.data.startswith("plan_duration:"), state=BotStates.waiting_plan_duration)
    dp.register_callback_query_handler(view_plans_complete_callback, lambda c: c.data == "view_plans_complete", state="*")
    
    # Handlers para configuração de upsell
    dp.register_callback_query_handler(config_upsell_callback, lambda c: c.data == "config_upsell", state="*")
    dp.register_callback_query_handler(edit_upsell_callback, lambda c: c.data == "edit_upsell", state="*")
    dp.register_callback_query_handler(toggle_upsell_callback, lambda c: c.data == "toggle_upsell", state="*")
    dp.register_message_handler(upsell_text_handler, state=BotStates.waiting_upsell_text)
    dp.register_message_handler(upsell_button_text_handler, state=BotStates.waiting_upsell_button_text)
    dp.register_message_handler(upsell_price_handler, state=BotStates.waiting_upsell_price)
    dp.register_message_handler(upsell_link_handler, state=BotStates.waiting_upsell_link)
    
    # Handlers para configuração de order bump
    dp.register_callback_query_handler(config_order_bump_callback, lambda c: c.data == "config_order_bump", state="*")
    dp.register_callback_query_handler(edit_order_bump_callback, lambda c: c.data == "edit_order_bump", state="*")
    dp.register_callback_query_handler(toggle_order_bump_callback, lambda c: c.data == "toggle_order_bump", state="*")
    dp.register_message_handler(order_bump_text_handler, state=BotStates.waiting_order_bump_text)
    dp.register_message_handler(order_bump_price_handler, state=BotStates.waiting_order_bump_price)
    dp.register_message_handler(order_bump_link_handler, state=BotStates.waiting_order_bump_link)
    
    # Handlers para remarketing
    dp.register_callback_query_handler(config_remarketing_callback, lambda c: c.data == "config_remarketing", state="*")
    dp.register_callback_query_handler(remarketing_target_callback, lambda c: c.data.startswith("remarketing_target:"), state="*")
    dp.register_callback_query_handler(remarketing_promotion_callback, lambda c: c.data.startswith("remarketing_promotion:"), state="*")
    dp.register_callback_query_handler(remarketing_plan_callback, lambda c: c.data.startswith("remarketing_plan:"), state="*")
    dp.register_message_handler(remarketing_price_handler, state=BotStates.waiting_remarketing_price)
    dp.register_message_handler(remarketing_message_handler, content_types=types.ContentTypes.ANY, state=BotStates.waiting_remarketing_message)
    dp.register_callback_query_handler(edit_remarketing_callback, lambda c: c.data == "edit_remarketing", state="*")
    dp.register_callback_query_handler(send_remarketing_callback, lambda c: c.data == "send_remarketing", state="*")
    
    # Handlers para seleção de planos
    dp.register_callback_query_handler(plan_callback, lambda c: c.data.startswith("plan:"), state="*")
    dp.register_callback_query_handler(order_bump_callback, lambda c: c.data == "order_bump", state="*")

# Inicialização

def setup_bot_handlers(dp: Dispatcher):
    """Configura os handlers para os bots dos usuários"""
    register_handlers(dp)