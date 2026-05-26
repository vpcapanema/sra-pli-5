"""Modelos do SRA — centraliza imports para o SQLAlchemy."""

from app.models.mixins import AuditoriaMixin
from app.models.usuario import Usuario
from app.models.dominio import Dominio
from app.models.modelo_relatorio import ModeloRelatorio
from app.models.relatorio_producao import RelatorioProducao
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.models.capitulo_documento import CapituloDocumento
from app.models.elemento_conteudo import ElementoConteudo
from app.models.envio_conteudo import EnvioConteudo
from app.models.previsualizacao_conteudo import PrevisualizacaoConteudo
from app.models.revisao import Revisao
from app.models.acao_revisao import AcaoRevisao
from app.models.bloqueio import Bloqueio
from app.models.biblioteca_formatacao import BibliotecaFormatacaoCanonica
from app.models.configuracao_numeracao import ConfiguracaoNumeracao
from app.models.notificacao import Notificacao
from app.models.registro_auditoria import RegistroAuditoria

__all__ = [
    'AuditoriaMixin',
    'Usuario',
    'Dominio',
    'ModeloRelatorio',
    'RelatorioProducao',
    'RelatorioFinalizado',
    'CapituloDocumento',
    'ElementoConteudo',
    'EnvioConteudo',
    'PrevisualizacaoConteudo',
    'Revisao',
    'AcaoRevisao',
    'Bloqueio',
    'BibliotecaFormatacaoCanonica',
    'ConfiguracaoNumeracao',
    'Notificacao',
    'RegistroAuditoria',
]
