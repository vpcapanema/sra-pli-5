"""Serviço de nivelamento de erros com wrapper de try-except centralizado.

Fornece um mecanismo padronizado para envolver qualquer função com tratamento
de exceções e retorno estruturado de erros, incluindo contexto e sugestões.

Propriedade 1 do design: Rastreabilidade Estruturada de Erros - toda operação
que falha retorna dict estruturado com sucesso=False, erro, sugestões.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Optional


class ServicoNiveladorErros:
    """Serviço para nivelamento e tratamento centralizado de erros."""

    # Mapeamento de tipos de exceção para sugestões padrão
    _SUGESTOES_PADRAO = {
        FileNotFoundError: "Arquivo não encontrado. Verifique o caminho.",
        PermissionError: "Permissão negada. Verifique as permissões do arquivo.",
        ValueError: "Valor inválido fornecido.",
        RuntimeError: "Erro durante execução.",
        KeyError: "Chave não encontrada no dicionário.",
        TypeError: "Tipo de dado incorreto.",
        AttributeError: "Atributo não encontrado no objeto.",
        ImportError: "Módulo ou dependência não encontrada.",
        OSError: "Erro de sistema operacional.",
        IOError: "Erro de entrada/saída.",
    }

    @staticmethod
    def executar_com_tratamento(
        funcao: Callable,
        *args,
        relatorio_id: Optional[int] = None,
        capitulo_id: Optional[int] = None,
        etapa: Optional[str] = None,
        usuario_id: Optional[int] = None,
        **kwargs,
    ) -> dict:
        """Executa uma função com tratamento de exceções centralizado.

        Envolve qualquer função com try-except, captura exceções e retorna
        um dicionário estruturado com informações do erro ou o resultado
        da função em caso de sucesso.

        Args:
            funcao: Função a ser executada.
            *args: Argumentos posicionais para a função.
            relatorio_id: ID do relatório relacionado (opcional).
            capitulo_id: ID do capítulo relacionado (opcional).
            etapa: Nome da etapa/operação (opcional).
            usuario_id: ID do usuário relacionado (opcional).
            **kwargs: Argumentos nomeados para a função.

        Returns:
            dict: Se sucesso, retorna o resultado da função.
                  Se erro, retorna dict estruturado com sucesso=False.
        """
        try:
            resultado = funcao(*args, **kwargs)
            return resultado
        except Exception as excecao:
            sugestoes = ServicoNiveladorErros._obter_sugestoes(excecao)
            dict_erro = ServicoNiveladorErros._construir_dict_erro(
                excecao=excecao,
                etapa=etapa,
                relatorio_id=relatorio_id,
                capitulo_id=capitulo_id,
                usuario_id=usuario_id,
                sugestoes=sugestoes,
            )
            ServicoNiveladorErros._registrar_log_erro(dict_erro)
            return dict_erro

    @staticmethod
    def _obter_sugestoes(excecao: Exception) -> list[str]:
        """Obtém sugestões apropriadas para o tipo de exceção.

        Args:
            excecao: Exceção capturada.

        Returns:
            list[str]: Lista de sugestões (pode ser vazia).
        """
        sugestoes = []
        tipo_excecao = type(excecao)
        
        # Verifica mapeamento direto
        if tipo_excecao in ServicoNiveladorErros._SUGESTOES_PADRAO:
            sugestoes.append(ServicoNiveladorErros._SUGESTOES_PADRAO[tipo_excecao])
        
        # Adiciona sugestão genérica se não houver específica
        if not sugestoes:
            sugestoes.append("Verifique os dados fornecidos e tente novamente.")
        
        return sugestoes

    @staticmethod
    def _construir_dict_erro(
        excecao: Exception,
        etapa: Optional[str] = None,
        relatorio_id: Optional[int] = None,
        capitulo_id: Optional[int] = None,
        usuario_id: Optional[int] = None,
        sugestoes: Optional[list[str]] = None,
    ) -> dict:
        """Constrói dicionário estruturado de erro.

        Args:
            excecao: Exceção capturada.
            etapa: Nome da etapa/operação (opcional).
            relatorio_id: ID do relatório relacionado (opcional).
            capitulo_id: ID do capítulo relacionado (opcional).
            usuario_id: ID do usuário relacionado (opcional).
            sugestoes: Lista de sugestões (opcional).

        Returns:
            dict: Dicionário estruturado de erro.
        """
        # Sanitizar mensagem de erro para remover informações sensíveis
        mensagem_erro = ServicoNiveladorErros._sanitizar_mensagem_erro(str(excecao))
        
        return {
            'sucesso': False,
            'erro': mensagem_erro,
            'tipo_erro': type(excecao).__name__,
            'etapa': etapa,
            'relatorio_id': relatorio_id,
            'capitulo_id': capitulo_id,
            'usuario_id': usuario_id,
            'sugestoes': sugestoes or [],
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _sanitizar_mensagem_erro(mensagem: str) -> str:
        """Remove informações sensíveis da mensagem de erro.
        
        Property 9: Segurança em Mensagens de Erro - mensagens NÃO devem
        conter caminhos absolutos, dados sensíveis (senhas, tokens) ou
        stack traces internas.
        
        Args:
            mensagem: Mensagem de erro original.
            
        Returns:
            str: Mensagem sanitizada.
        """
        # Padrões de informações sensíveis
        padroes_sensiveis = [
            # Caminhos absolutos
            (r'/[^/\s]+(/[^/\s]+)*\.\w+', 'arquivo'),
            (r'[A-Za-z]:\\[^\\]+(\\[^\\]+)*\.\w+', 'arquivo'),
            (r'/home/[^/\s]+/', 'diretório do usuário'),
            (r'/etc/', 'diretório de configuração'),
            (r'/var/', 'diretório do sistema'),
            
            # Credenciais e tokens
            (r'Token:\s*\S+', 'token'),
            (r'API[_-]?[Kk]ey:\s*\S+', 'chave de API'),
            (r'[Ss]ecret:\s*\S+', 'segredo'),
            (r'[Pp]assword=\S+', 'senha'),
            (r'[Pp]wd=\S+', 'senha'),
            (r'API Key:\s*\S+', 'chave de API'),
            
            # URLs com credenciais
            (r'://[^:]+:[^@]+@', 'credenciais em URL'),
            
            # Endereços IP internos
            (r'\b(?:10\.|127\.|172\.(?:1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)\d{1,3}\.\d{1,3}\b', 'endereço IP interno'),
        ]
        
        mensagem_sanitizada = mensagem
        
        for padrao, tipo in padroes_sensiveis:
            if re.search(padrao, mensagem_sanitizada):
                # Substituir por descrição genérica
                mensagem_sanitizada = re.sub(padrao, f'[{tipo} removido por segurança]', mensagem_sanitizada)
        
        return mensagem_sanitizada

    @staticmethod
    def _registrar_log_erro(dict_erro: dict) -> None:
        """Registra erro no logger estruturado.

        Args:
            dict_erro: Dicionário estruturado de erro.
        """
        logger = logging.getLogger(__name__)
        
        mensagem = (
            f"Erro na etapa '{dict_erro.get('etapa', 'N/A')}': "
            f"{dict_erro['tipo_erro']} - {dict_erro['erro']}"
        )
        
        contexto = {
            'relatorio_id': dict_erro.get('relatorio_id'),
            'capitulo_id': dict_erro.get('capitulo_id'),
            'usuario_id': dict_erro.get('usuario_id'),
            'sugestoes': dict_erro.get('sugestoes', []),
            'timestamp': dict_erro.get('timestamp'),
        }
        
        logger.error(mensagem, extra={'contexto': contexto})

    @staticmethod
    def adicionar_sugestao_padrao(
        tipo_excecao: type,
        sugestao: str,
    ) -> None:
        """Adiciona ou atualiza uma sugestão padrão para um tipo de exceção.

        Args:
            tipo_excecao: Tipo da exceção (classe).
            sugestao: Sugestão de correção.
        """
        ServicoNiveladorErros._SUGESTOES_PADRAO[tipo_excecao] = sugestao

    @staticmethod
    def obter_sugestoes_padrao() -> dict:
        """Retorna cópia do mapeamento de sugestões padrão.

        Returns:
            dict: Cópia do dicionário de sugestões padrão.
        """
        return ServicoNiveladorErros._SUGESTOES_PADRAO.copy()