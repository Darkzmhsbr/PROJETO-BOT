#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Constantes utilizadas no sistema
"""

# Estados FSM para fluxos do bot
class States:
    # Estados do bot gerenciador
    VERIFICATION = "verification"
    CREATING_BOT = "creating_bot"
    WAITING_TOKEN = "waiting_token"
    MANAGING_BOTS = "managing_bots"
    
    # Estados do bot de usuário
    CONFIGURING_MESSAGES = "configuring_messages"
    WAITING_MESSAGE_TEXT = "waiting_message_text"
    WAITING_MESSAGE_MEDIA = "waiting_message_media"
    WAITING_PUSHINPAY_TOKEN = "waiting_pushinpay_token"
    ADDING_CHAT = "adding_chat"
    WAITING_CHAT_ID = "waiting_chat_id"
    CONFIGURING_SUPPORT = "configuring_support"
    CONFIGURING_UPSELL = "configuring_upsell"
    CONFIGURING_ORDER_BUMP = "configuring_order_bump"
    CONFIGURING_REMARKETING = "configuring_remarketing"
    CREATING_PLAN = "creating_plan"
    WAITING_PLAN_PRICE = "waiting_plan_price"

# Tipos de plano
class PlanTypes:
    ONE_DAY = "1_day"
    SEVEN_DAYS = "7_days"
    FIFTEEN_DAYS = "15_days"
    THIRTY_DAYS = "30_days"
    THREE_MONTHS = "3_months"
    SIX_MONTHS = "6_months"
    ONE_YEAR = "1_year"
    LIFETIME = "lifetime"

# Tipos de mensagem
class MessageTypes:
    TEXT = "text"
    MEDIA = "media"
    MEDIA_WITH_TEXT = "media_with_text"

# Status de pagamento
class PaymentStatus:
    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    FAILED = "failed"

# Status do bot
class BotStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    DELETED = "deleted"

# Comandos
COMMANDS = {
    "start": "Iniciar o bot",
    "help": "Exibir ajuda",
    "suporte": "Entrar em contato com o suporte",
    "planos": "Ver planos disponíveis",
    "status": "Verificar status da assinatura",
}

# Mensagens padrão
DEFAULT_MESSAGES = {
    "welcome": "🔒 VERIFICAÇÃO NECESSÁRIA\n\nPara usar todas as funcionalidades do bot, você precisa entrar no nosso canal oficial:",
    "not_in_channel": "❌ Você ainda não entrou no canal. Por favor, entre no canal e tente novamente.",
    "verified": "✅ Verificação concluída! Agora você pode usar todas as funcionalidades do bot.",
    "bot_description": "🔥 BOT CRIADOR DE BOTS 🔥\n\nEste bot permite criar seu próprio bot para gerenciar grupos VIP com sistema de pagamento integrado.",
    "bot_creation_instructions": "🤖 CRIAR SEU BOT\n\nPara criar seu próprio bot, siga os passos abaixo:\n\n1️⃣Acesse @BotFather no Telegram\n2️⃣Envie /newbot e siga as instruções\n3️⃣Após criar o bot, copie o token que o BotFather enviar\n4️⃣Cole o token aqui neste chat\n\nO token se parece com algo assim: 123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ",
    "waiting_token": "Por favor, envie o token do seu bot gerado pelo @BotFather.",
    "invalid_token": "❌ Token inválido. Por favor, verifique e tente novamente.",
    "bot_starting": "🔄 INICIANDO SEU BOT...\n\nSeu bot está sendo iniciado. Este processo pode levar alguns segundos.",
    "bot_started": "✅ BOT INICIADO COM SUCESSO!\n\nSeu bot @{username} está online e pronto para uso.\n\nConfigure as opções do seu bot enviando o comando /start para ele.",
    "bot_created": "✅ BOT CRIADO COM SUCESSO!\n\nSeu bot @{username} foi criado e configurado com sucesso!\n\nClique no botão abaixo para iniciar seu bot:",
}