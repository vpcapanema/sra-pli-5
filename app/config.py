"""Configurações da aplicação Flask SRA."""

import os
from dotenv import load_dotenv

load_dotenv()


def _normalizar_database_url(url: str) -> str:
    """Garante que a URL aponte para o driver psycopg 3.

    O projeto usa `psycopg[binary]` (psycopg 3). O SQLAlchemy, ao receber
    uma URL `postgresql://...` sem driver explícito, tenta carregar
    `psycopg2`, que não é instalado. Esta função reescreve o esquema
    para `postgresql+psycopg://...` quando aplicável, sem alterar o
    restante da URL. Demais esquemas (sqlite, postgres+psycopg, etc.)
    são preservados.
    """
    if not url:
        return url
    if url.startswith('postgresql+'):
        return url
    if url.startswith('postgresql://'):
        return 'postgresql+psycopg://' + url[len('postgresql://'):]
    if url.startswith('postgres://'):
        return 'postgresql+psycopg://' + url[len('postgres://'):]
    return url


class Config:
    """Classe de configuração da aplicação."""
    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 'chave-dev-temporaria'
    )
    SQLALCHEMY_DATABASE_URI = _normalizar_database_url(
        os.environ.get('DATABASE_URL', 'sqlite:///sra.db')
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
