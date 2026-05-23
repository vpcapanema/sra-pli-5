"""Configurações da aplicação Flask SRA."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Classe de configuração da aplicação."""
    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 'chave-dev-temporaria'
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///sra.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STORAGE_PATH = os.environ.get(
        'STORAGE_PATH',
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'storage'
        )
    )

    BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
    BREVO_FROM_EMAIL = os.environ.get(
        'BREVO_FROM_EMAIL',
        'no-reply@vpc-websistemas.com.br'
    )
    BREVO_FROM_NAME = os.environ.get(
        'BREVO_FROM_NAME', 'SRA · PLI-SP'
    )
    APP_BASE_URL = os.environ.get(
        'APP_BASE_URL', 'http://localhost:5000'
    )
