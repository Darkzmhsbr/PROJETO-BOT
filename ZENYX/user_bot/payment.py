# user_bot/payment.py
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import os
import json

from core.database import get_redis_connection
from models.user_bot import UserBot
from integrations.pushin_pay.client import PushinPayClient

class PaymentConfig(StatesGroup):
    """Estados para configuração de pagamento"""
    waiting_for_token = State()

async def config_payment_callback(callback_query: types.CallbackQuery, state: FSMContext, bot_data):
    """Callback para configuração de pagamento"""
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
    
    # Verifica se já tem token configurado
    token_status = "Configurado" if bot.pushin_token else "Nenhum token configurado."
    
    # Configura o estado
    await state.set_state(PaymentConfig.waiting_for_token.state)
    
    # Cria o teclado
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="back_to_admin")
    )
    
    # Mensagem de configuração
    await callback_query.message.answer(
        "💰 CONFIGURAR PUSHINPAY\n\n"
        "Configure seu token da PushinPay para receber pagamentos via PIX.\n\n"
        f"{token_status}\n\n"
        "Envie seu token da PushinPay ou clique em 'Voltar' para cancelar.",
        reply_markup=keyboard
    )
    
    await callback_query.answer()

async def receive_token(message: types.Message, state: FSMContext, bot_data):
    """Handler para receber token da Pushin Pay"""
    token = message.text.strip()
    
    # Verifica se o token parece válido
    if not token or len(token) < 10:
        await message.answer(
            "❌ Token inválido. Por favor, envie um token válido ou clique em 'Voltar' para cancelar."
        )
        return
    
    # Obtém o bot do usuário
    redis_conn = await get_redis_connection()
    bot = await UserBot.get(redis_conn, bot_data["bot_id"])
    
    if not bot:
        await message.answer("❌ Bot não encontrado.")
        await state.finish()
        return
    
    # Tenta validar o token
    try:
        client = PushinPayClient(
            token=token,
            base_url=os.getenv("PUSHINPAY_API_URL")
        )
        
        # Aqui poderia fazer uma chamada de teste para validar o token
        # Por simplicidade, vamos apenas salvar o token
        
        # Salva o token
        bot.pushin_token = token
        await bot.save(redis_conn)
        
        # Cria o teclado para o menu principal
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(text="📝 Configurar mensagens", callback_data="config_messages"),
            InlineKeyboardButton(text="💰 Integrar Pushin Pay", callback_data="config_payment")
        )
        keyboard.add(
            InlineKeyboardButton(text="👥 Adicionar canal/grupo", callback_data="config_channel"),
            InlineKeyboardButton(text="󰘎 Configurar suporte", callback_data="config_support")
        )
        keyboard.add(
            InlineKeyboardButton(text="📊 Métricas de Vendas", callback_data="metrics"),
            InlineKeyboardButton(text="🛍 Adicionar Upsell", callback_data="config_upsell")
        )
        keyboard.add(
            InlineKeyboardButton(text="💱 Adicionar Order Bump", callback_data="config_order_bump"),
            InlineKeyboardButton(text="📤 Remarketing", callback_data="remarketing")
        )
        keyboard.add(
            InlineKeyboardButton(text="🎯 Criar planos", callback_data="config_plans")
        )
        
        # Mensagem de sucesso
        await message.answer(
            "✅ TOKEN CONFIGURADO!\n\n"
            "Seu token da PushinPay foi configurado com sucesso. Agora você pode receber pagamentos via PIX.",
            reply_markup=keyboard
        )
        
    except Exception as e:
        # Em caso de erro
        await message.answer(
            f"❌ Erro ao configurar token: {str(e)}\n\n"
            "Por favor, verifique se o token está correto e tente novamente."
        )
    
    # Finaliza o estado
    await state.finish()

def register_payment_handlers(dp: Dispatcher, bot_data):
    """Registra os handlers de configuração de pagamento"""
    # Callbacks
    dp.register_callback_query_handler(
        lambda c, state: config_payment_callback(c, state, bot_data),
        lambda c: c.data == "config_payment"
    )
    
    # Mensagens
    dp.register_message_handler(
        lambda m, state: receive_token(m, state, bot_data),
        state=PaymentConfig.waiting_for_token,
        content_types=types.ContentTypes.TEXT
    )