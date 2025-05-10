# user_bot/message_config.py
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import json

from core.database import get_redis_connection
from models.user_bot import UserBot

class MessageConfig(StatesGroup):
    """Estados para configuração de mensagens"""
    waiting_for_content_type = State()
    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_media_caption = State()
    waiting_for_edit_selection = State()
    waiting_for_edit_text = State()
    waiting_for_edit_media = State()

async def config_messages_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_data):
    """Callback para configuração de mensagens"""
    user_id = callback_query.from_user.id
    
    # Verifica se o usuário é o dono do bot
    if user_id != bot_data["user_id"]:
        await callback_query.answer("❌ Você não tem permissão para configurar este bot.")
        return
    
    # Obtém o bot do usuário
    redis_conn = await get_redis_connection()
    bot = await UserBot.get(redis_conn, bot_data["bot_id"])
    
    if not bot:
        await callback_query.answer("❌ Bot não encontrado.")
        return
    
    # Cria o teclado
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="📝 Nova mensagem", callback_data="new_message"),
        InlineKeyboardButton(text="👀 Visualizar todas", callback_data="view_messages")
    )
    keyboard.add(
        InlineKeyboardButton(text="📝 Editar mensagens", callback_data="edit_messages"),
        InlineKeyboardButton(text="📤 Ordem das mensagens", callback_data="message_order")
    )
    keyboard.add(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
    )
    
    # Mensagem de configuração
    await callback_query.message.answer(
        f"⚙️ Configuração de Boas-vindas\n\n"
        f"📝 Total de mensagens: {len(bot.welcome_messages)}\n\n"
        f"Gerencie as mensagens de boas-vindas que seus usuários receberão ao iniciar o bot.\n\n"
        f"ℹ️ As mensagens serão enviadas na ordem configurada.",
        reply_markup=keyboard
    )
    
    await callback_query.answer()

async def new_message_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_data):
    """Callback para nova mensagem"""
    # Cria o teclado
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="📝 Apenas texto", callback_data="new_text_message"),
        InlineKeyboardButton(text="🖼 Mídia + texto", callback_data="new_media_message")
    )
    keyboard.add(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages")
    )
    
    # Mensagem de seleção de tipo
    await callback_query.message.answer(
        "📝 Nova Mensagem de Boas-vindas\n\n"
        "Escolha o tipo de conteúdo para esta mensagem:",
        reply_markup=keyboard
    )
    
    await callback_query.answer()

async def new_text_message_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_data):
    """Callback para nova mensagem de texto"""
    # Configura o estado
    await state.set_state(MessageConfig.waiting_for_text.state)
    await state.update_data(message_type="text")
    
    # Cria o teclado
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_message_config")
    )
    
    # Mensagem de solicitação
    await callback_query.message.answer(
        "✏️ Digite o texto da mensagem de boas-vindas:",
        reply_markup=keyboard
    )
    
    await callback_query.answer()

async def new_media_message_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_data):
    """Callback para nova mensagem com mídia"""
    # Configura o estado
    await state.set_state(MessageConfig.waiting_for_media.state)
    await state.update_data(message_type="media_text")
    
    # Cria o teclado
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_message_config")
    )
    
    # Mensagem de solicitação
    await callback_query.message.answer(
        "🖼 Envie a mídia (foto, vídeo ou GIF):",
        reply_markup=keyboard
    )
    
    await callback_query.answer()

async def receive_text_message(message: types.Message, state: FSMContext, bot_data):
    """Handler para receber mensagem de texto"""
    # Obtém os dados do estado
    data = await state.get_data()
    message_type = data.get("message_type")
    
    if message_type != "text":
        return
    
    # Obtém o bot do usuário
    redis_conn = await get_redis_connection()
    bot = await UserBot.get(redis_conn, bot_data["bot_id"])
    
    if not bot:
        await message.answer("❌ Bot não encontrado.")
        await state.finish()
        return
    
    # Cria a nova mensagem
    new_message = {
        "id": len(bot.welcome_messages) + 1,
        "type": "text",
        "content": message.text
    }
    
    # Adiciona a mensagem
    bot.welcome_messages.append(new_message)
    
    # Salva o bot
    await bot.save(redis_conn)
    
    # Cria o teclado
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="📝 Nova mensagem", callback_data="new_message"),
        InlineKeyboardButton(text="👀 Visualizar todas", callback_data="view_messages")
    )
    keyboard.add(
        InlineKeyboardButton(text="📝 Editar mensagens", callback_data="edit_messages"),
        InlineKeyboardButton(text="📤 Ordem das mensagens", callback_data="message_order")
    )
    keyboard.add(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
    )
    
    # Mensagem de sucesso
    await message.answer(
        "✅ Mensagem adicionada com sucesso!",
        reply_markup=keyboard
    )
    
    # Finaliza o estado
    await state.finish()

async def receive_media_message(message: types.Message, state: FSMContext, bot_data):
    """Handler para receber mensagem com mídia"""
    # Verifica se a mensagem tem mídia
    if not (message.photo or message.video or message.animation):
        await message.answer("❌ Por favor, envie uma foto, vídeo ou GIF.")
        return
    
    # Obtém os dados do estado
    data = await state.get_data()
    message_type = data.get("message_type")
    
    if message_type != "media_text":
        return
    
    # Determina o tipo de mídia e obtém o ID
    if message.photo:
        media_type = "photo"
        media_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_id = message.video.file_id
    elif message.animation:
        media_type = "animation"
        media_id = message.animation.file_id
    else:
        await message.answer("❌ Formato de mídia não suportado.")
        return
    
    # Atualiza o estado
    await state.update_data(
        media_type=media_type,
        media_id=media_id
    )
    
    # Configura o próximo estado
    await state.set_state(MessageConfig.waiting_for_media_caption.state)
    
    # Cria o teclado
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_message_config")
    )
    
    # Mensagem de solicitação
    await message.answer(
        "✅ Mídia recebida com sucesso!\n\n"
        "Agora, envie o texto que acompanhará esta mídia (ou envie /pular para usar apenas a mídia):",
        reply_markup=keyboard
    )

async def receive_media_caption(message: types.Message, state: FSMContext, bot_data):
    """Handler para receber legenda da mídia"""
    # Obtém os dados do estado
    data = await state.get_data()
    message_type = data.get("message_type")
    media_type = data.get("media_type")
    media_id = data.get("media_id")
    
    if message_type != "media_text" or not media_id:
        return
    
    # Verifica se é para pular a legenda
    caption = None
    if message.text != "/pular":
        caption = message.text
    
    # Obtém o bot do usuário
    redis_conn = await get_redis_connection()
    bot = await UserBot.get(redis_conn, bot_data["bot_id"])
    
    if not bot:
        await message.answer("❌ Bot não encontrado.")
        await state.finish()
        return
    
    # Cria a nova mensagem
    new_message = {
        "id": len(bot.welcome_messages) + 1,
        "type": "media_text",
        "media_type": media_type,
        "media_id": media_id,
        "text": caption
    }
    
    # Adiciona a mensagem
    bot.welcome_messages.append(new_message)
    
    # Salva o bot
    await bot.save(redis_conn)
    
    # Cria o teclado
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="📝 Nova mensagem", callback_data="new_message"),
        InlineKeyboardButton(text="👀 Visualizar todas", callback_data="view_messages")
    )
    keyboard.add(
        InlineKeyboardButton(text="📝 Editar mensagens", callback_data="edit_messages"),
        InlineKeyboardButton(text="📤 Ordem das mensagens", callback_data="message_order")
    )
    keyboard.add(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
    )
    
    # Mensagem de sucesso
    await message.answer(
        "✅ Mensagem com mídia adicionada com sucesso!",
        reply_markup=keyboard
    )
    
    # Finaliza o estado
    await state.finish()

async def view_messages_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_data):
    """Callback para visualizar mensagens"""
    # Obtém o bot do usuário
    redis_conn = await get_redis_connection()
    bot = await UserBot.get(redis_conn, bot_data["bot_id"])
    
    if not bot:
        await callback_query.answer("❌ Bot não encontrado.")
        return
    
    # Verifica se há mensagens
    if not bot.welcome_messages:
        # Cria o teclado
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="📝 Nova mensagem", callback_data="new_message"),
            InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages")
        )
        
        await callback_query.message.answer(
            "❌ Nenhuma mensagem configurada ainda.\n\n"
            "Clique em 'Nova mensagem' para adicionar uma mensagem de boas-vindas.",
            reply_markup=keyboard
        )
        
        await callback_query.answer()
        return
    
    # Envia as mensagens em sequência
    for msg in bot.welcome_messages:
        if msg["type"] == "text":
            await callback_query.message.answer(msg["content"])
        elif msg["type"] == "media_text":
            if msg["media_type"] == "photo":
                await callback_query.message.answer_photo(
                    photo=msg["media_id"],
                    caption=msg.get("text", "")
                )
            elif msg["media_type"] == "video":
                await callback_query.message.answer_video(
                    video=msg["media_id"],
                    caption=msg.get("text", "")
                )
            elif msg["media_type"] == "animation":
                await callback_query.message.answer_animation(
                    animation=msg["media_id"],
                    caption=msg.get("text", "")
                )
    
    # Cria o teclado
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages")
    )
    
    # Mensagem final
    await callback_query.message.answer(
        "👀 Visualização das Mensagens de Boas-vindas\n\n"
        "Mensagens enviadas em sequência.",
        reply_markup=keyboard
    )
    
    await callback_query.answer()

async def edit_messages_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_data):
    """Callback para editar mensagens"""
    # Obtém o bot do usuário
    redis_conn = await get_redis_connection()
    bot = await UserBot.get(redis_conn, bot_data["bot_id"])
    
    if not bot:
        await callback_query.answer("❌ Bot não encontrado.")
        return
    
    # Verifica se há mensagens
    if not bot.welcome_messages:
        # Cria o teclado
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="📝 Nova mensagem", callback_data="new_message"),
            InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages")
        )
        
        await callback_query.message.answer(
            "❌ Nenhuma mensagem configurada ainda.\n\n"
            "Clique em 'Nova mensagem' para adicionar uma mensagem de boas-vindas.",
            reply_markup=keyboard
        )
        
        await callback_query.answer()
        return
    
    # Cria o teclado
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    # Adiciona botões para cada mensagem
    for i, msg in enumerate(bot.welcome_messages):
        if msg["type"] == "text":
            button_text = f"Mensagem de texto: {msg['content'][:30]}..."
        else:
            button_text = f"Mensagem de mídia+texto"
        
        keyboard.add(
            InlineKeyboardButton(text=button_text, callback_data=f"edit_message:{i}")
        )
    
    # Adiciona botão para apagar todas
    keyboard.add(
        InlineKeyboardButton(text="🗑 Apagar todas as mensagens", callback_data="delete_all_messages")
    )
    
    # Adiciona botão para voltar
    keyboard.add(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="config_messages")
    )
    
    # Mensagem de edição
    await callback_query.message.answer(
        "📝 Editar Mensagens\n\n"
        "Selecione uma mensagem para editar ou excluir:",
        reply_markup=keyboard
    )
    
    await callback_query.answer()

# Registra todos os handlers
def register_message_handlers(dp: Dispatcher, bot_data):
    """Registra os handlers de configuração de mensagens"""
    # Callbacks
    dp.register_callback_query_handler(
        lambda c, state: config_messages_callback(c, state, bot_data),
        lambda c: c.data == "config_messages"
    )
    
    dp.register_callback_query_handler(
        lambda c, state: new_message_callback(c, state, bot_data),
        lambda c: c.data == "new_message"
    )
    
    dp.register_callback_query_handler(
        lambda c, state: new_text_message_callback(c, state, bot_data),
        lambda c: c.data == "new_text_message"
    )
    
    dp.register_callback_query_handler(
        lambda c, state: new_media_message_callback(c, state, bot_data),
        lambda c: c.data == "new_media_message"
    )
    
    dp.register_callback_query_handler(
        lambda c, state: view_messages_callback(c, state, bot_data),
        lambda c: c.data == "view_messages"
    )
    
    dp.register_callback_query_handler(
        lambda c, state: edit_messages_callback(c, state, bot_data),
        lambda c: c.data == "edit_messages"
    )
    
    # Mensagens
    dp.register_message_handler(
        lambda m, state: receive_text_message(m, state, bot_data),
        state=MessageConfig.waiting_for_text,
        content_types=types.ContentTypes.TEXT
    )
    
    dp.register_message_handler(
        lambda m, state: receive_media_message(m, state, bot_data),
        state=MessageConfig.waiting_for_media,
        content_types=types.ContentTypes.PHOTO | types.ContentTypes.VIDEO | types.ContentTypes.ANIMATION
    )
    
    dp.register_message_handler(
        lambda m, state: receive_media_caption(m, state, bot_data),
        state=MessageConfig.waiting_for_media_caption,
        content_types=types.ContentTypes.TEXT
    )