"""Sistema de logging do SRA para exibição no navegador."""

import logging
import threading
from datetime import datetime
from flask import request, session
from flask_login import current_user


class SRALogHandler(logging.Handler):
    """Handler personalizado que armazena logs em memória
    para exibição no navegador."""

    def __init__(self, max_logs=500):
        super().__init__()
        self.logs = []
        self.max_logs = max_logs
        self.lock = threading.Lock()

    def emit(self, record):
        """Adiciona log à lista em memória."""
        try:
            with self.lock:
                user_name = 'anonymous'
                try:
                    if current_user.is_authenticated:
                        user_name = getattr(
                            current_user, 'nome', 'anonymous'
                        )
                except Exception:
                    pass

                perfil = ''
                try:
                    perfil = session.get('perfil_ativo', '')
                except Exception:
                    pass

                path = ''
                method = ''
                try:
                    path = request.path
                    method = request.method
                except Exception:
                    pass

                log_entry = {
                    'timestamp': datetime.fromtimestamp(
                        record.created
                    ).isoformat(),
                    'level': record.levelname,
                    'message': self.format(record),
                    'logger': record.name,
                    'user': user_name,
                    'perfil': perfil,
                    'path': path,
                    'method': method,
                }
                self.logs.append(log_entry)
                # Manter apenas os últimos max_logs
                if len(self.logs) > self.max_logs:
                    self.logs = self.logs[-self.max_logs:]
        except Exception:
            self.handleError(record)

    def get_logs(self, level=None, limit=100):
        """Retorna logs filtrados."""
        with self.lock:
            if level:
                filtered = [log for log in self.logs if log['level'] == level]
            else:
                filtered = self.logs
            return filtered[-limit:]


# Instância global do handler
sra_log_handler = SRALogHandler()
sra_log_handler.setLevel(logging.INFO)

# Formatação dos logs
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
sra_log_handler.setFormatter(formatter)


def log_action(action, details=None, level='INFO'):
    """Registra uma ação do usuário no sistema de logs."""
    logger = logging.getLogger('sra.action')
    if not logger.handlers:
        logger.addHandler(sra_log_handler)
        logger.setLevel(logging.INFO)

    message = f"Ação: {action}"
    if details:
        message += f" | Detalhes: {details}"

    if level == 'INFO':
        logger.info(message)
    elif level == 'WARNING':
        logger.warning(message)
    elif level == 'ERROR':
        logger.error(message)
    elif level == 'DEBUG':
        logger.debug(message)


def setup_sra_logging(app):
    """Configura o logging personalizado para a aplicação Flask."""
    # Adicionar handler ao logger principal
    app.logger.addHandler(sra_log_handler)
    app.logger.setLevel(logging.INFO)
