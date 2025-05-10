#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Arquivo principal que inicia o bot gerenciador e o sistema de bots de usuários
simultaneamente usando processamento assíncrono.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Configuração de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

if LOG_LEVEL == 'DEBUG':
    logging.getLogger().setLevel(logging.DEBUG)
elif LOG_LEVEL == 'INFO':
    logging.getLogger().setLevel(logging.INFO)
elif LOG_LEVEL == 'WARNING':
    logging.getLogger().setLevel(logging.WARNING)
elif LOG_LEVEL == 'ERROR':
    logging.getLogger().setLevel(logging.ERROR)

async def start_main_bot():
    """Inicia o bot gerenciador principal"""
    from main import run_main_bot
    await run_main_bot()

async def start_user_bots():
    """Inicia o sistema de bots dos usuários"""
    from user_bot_main import run_user_bots
    await run_user_bots()

async def main():
    """Função principal que executa ambos os bots em paralelo"""
    logger.info("Iniciando sistema Zenyx VIPs...")
    tasks = [
        asyncio.create_task(start_main_bot()),
        asyncio.create_task(start_user_bots())
    ]
    
    # Executa ambas as tarefas simultaneamente
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        # Configura e inicia o loop de eventos
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Sistema encerrado pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)