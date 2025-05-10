#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bot gerenciador principal (Zenyx VIPs).
Responsável por gerenciar a criação de bots de usuários e verificar 
acesso ao canal oficial.
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.utils import executor
from dotenv import load_dotenv

from config.settings import get_redis_url
from core.database import Database
from core.bot_manager import BotManager
from handlers.verification_handlers import register_verification_handlers
from handlers.user_handlers import register_user_handlers
from handlers.admin_handlers import register_admin_handlers

# Carrega variáveis de ambiente
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))

# Configuração de logs
logger = logging.getLogger(__name__)

# Inicializa o bot e o dispatcher
bot = Bot(token=BOT_TOKEN)
storage = RedisStorage2(url=get_redis_url())
dp = Dispatcher(bot, storage=storage)

# Inicializa gerenciador de banco de dados
db = Database()

# Inicializa gerenciador de bots
bot_manager = BotManager(bot, db)

async def on_startup(dp):
    """Ações executadas ao iniciar o bot"""
    logger.info("Bot gerenciador iniciado")
    
    # Registra os handlers
    register_verification_handlers(dp, bot, db)
    register_user_handlers(dp, bot, bot_manager, db)
    register_admin_handlers(dp, bot, bot_manager, db)
    
    # Notifica administradores
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🚀 Bot gerenciador iniciado com sucesso!")
        except Exception as e:
            logger.error(f"Não foi possível notificar o administrador {admin_id}: {e}")

async def on_shutdown(dp):
    """Ações executadas ao desligar o bot"""
    logger.info("Desligando bot gerenciador")
    await bot.close()
    await storage.close()

async def run_main_bot():
    """Inicia o bot gerenciador"""
    await dp.start_polling(on_startup=on_startup, on_shutdown=on_shutdown)

if __name__ == "__main__":
    asyncio.run(run_main_bot())