#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configurações gerais do sistema
"""

import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do Bot Principal
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')

# Configurações de Administração
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))

# Configurações de Canal
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 0))
CHANNEL_LINK = os.getenv('CHANNEL_LINK')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')

# Configurações PushinPay
PUSHINPAY_TOKEN = os.getenv('PUSHINPAY_TOKEN')
PUSHINPAY_API_URL = os.getenv('PUSHINPAY_API_URL')

# Configurações Redis
REDIS_URL = os.getenv('REDIS_URL')

# Configurações de Pagamento
PAYMENT_FEE = float(os.getenv('PAYMENT_FEE', 0.30))
COMMISSION_RATE = float(os.getenv('COMMISSION_RATE', 0.20))
MIN_WITHDRAWAL = float(os.getenv('MIN_WITHDRAWAL', 30.00))
WITHDRAWAL_INTERVAL_DAYS = int(os.getenv('WITHDRAWAL_INTERVAL_DAYS', 1))

# Configurações de Referência
REFERRAL_BONUS = float(os.getenv('REFERRAL_BONUS', 125.00))
REFERRAL_MIN_SALES = int(os.getenv('REFERRAL_MIN_SALES', 3))
REFERRAL_MIN_AMOUNT = float(os.getenv('REFERRAL_MIN_AMOUNT', 9.90))
REFERRAL_EXPIRY_DAYS = int(os.getenv('REFERRAL_EXPIRY_DAYS', 15))

# Admin VIP
ADMIN_VIP_PRICE = float(os.getenv('ADMIN_VIP_PRICE', 97.90))
ADMIN_VIP_TRIAL_DAYS = int(os.getenv('ADMIN_VIP_TRIAL_DAYS', 30))

# Configurações Gerais
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Timeouts
PAYMENT_TIMEOUT_MINUTES = int(os.getenv('PAYMENT_TIMEOUT_MINUTES', 30))
CODE_EXPIRY_HOURS = int(os.getenv('CODE_EXPIRY_HOURS', 1))

# Limites
MAX_BOTS_PER_USER = int(os.getenv('MAX_BOTS_PER_USER', 30))
MAX_GROUPS_PER_BOT = int(os.getenv('MAX_GROUPS_PER_BOT', 20))

def get_redis_url():
    """Retorna a URL de conexão com o Redis"""
    return REDIS_URL