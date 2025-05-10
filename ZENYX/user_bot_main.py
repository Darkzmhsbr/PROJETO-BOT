#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sistema de bots de usuários.
Responsável por gerenciar e manter online todos os bots criados pelos usuários.
"""

import asyncio
import logging
import os
from aiogram import Bot
from dotenv import load_dotenv

from config.settings import get_redis_url
from core.database import Database
from core.bot_manager import BotManager, UserBot
from user_bot.handlers import create_user_bot_dispatcher

# Configuração de logs
logger = logging.getLogger(__name__)

# Inicializa o banco de dados
db = Database()

# Inicializa dicionário de bots ativos
active_bots = {}

async def load_user_bots():
    """Carrega todos os bots de usuários do banco de dados"""
    logger.info("Carregando bots de usuários...")
    user_bots = await db.get_all_user_bots()
    logger.info(f"Total de {len(user_bots)} bots encontrados")
    return user_bots

async def start_user_bot(token, bot_data):
    """Inicia um bot de usuário"""
    try:
        bot = Bot(token=token)
        user_bot = UserBot(bot, bot_data, db)
        dispatcher = create_user_bot_dispatcher(user_bot)
        
        logger.info(f"Iniciando bot @{(await bot.me).username}")
        
        # Armazena referência do bot ativo
        active_bots[token] = {
            'bot': bot,
            'dispatcher': dispatcher,
            'task': None
        }
        
        # Inicia o polling do bot
        task = asyncio.create_task(dispatcher.start_polling())
        active_bots[token]['task'] = task
        
        # Atualiza status no banco de dados
        await db.update_user_bot_status(bot_data['id'], True)
        
        return True
    except Exception as e:
        logger.error(f"Erro ao iniciar bot: {e}", exc_info=True)
        await db.update_user_bot_status(bot_data['id'], False)
        return False

async def stop_user_bot(token):
    """Para um bot de usuário"""
    if token in active_bots:
        try:
            # Cancela a task de polling
            if active_bots[token]['task']:
                active_bots[token]['task'].cancel()
            
            # Fecha a conexão do bot
            await active_bots[token]['bot'].close()
            
            # Remove do dicionário de bots ativos
            del active_bots[token]
            return True
        except Exception as e:
            logger.error(f"Erro ao parar bot: {e}", exc_info=True)
    return False

async def monitor_new_bots():
    """Monitora e inicia novos bots adicionados ao banco de dados"""
    last_check = 0
    
    while True:
        try:
            # Verifica se há novos bots desde a última verificação
            new_bots = await db.get_new_user_bots(last_check)
            
            for bot_data in new_bots:
                token = bot_data['token']
                if token not in active_bots:
                    logger.info(f"Novo bot detectado: ID {bot_data['id']}")
                    await start_user_bot(token, bot_data)
            
            # Atualiza timestamp da última verificação
            if new_bots:
                last_check = max(bot['created_at'] for bot in new_bots)
                
            # Verifica também bots que devem ser parados
            stopped_bots = await db.get_stopped_user_bots()
            for bot_data in stopped_bots:
                token = bot_data['token']
                if token in active_bots:
                    logger.info(f"Parando bot: ID {bot_data['id']}")
                    await stop_user_bot(token)
            
            # Aguarda antes da próxima verificação
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Erro ao monitorar novos bots: {e}", exc_info=True)
            await asyncio.sleep(10)

async def run_user_bots():
    """Inicia o sistema de bots de usuários"""
    logger.info("Iniciando sistema de bots de usuários")
    
    # Carrega bots existentes
    user_bots = await load_user_bots()
    
    # Inicia cada bot
    for bot_data in user_bots:
        if bot_data.get('status', False):
            await start_user_bot(bot_data['token'], bot_data)
    
    # Inicia o monitoramento de novos bots
    await monitor_new_bots()

if __name__ == "__main__":
    asyncio.run(run_user_bots())