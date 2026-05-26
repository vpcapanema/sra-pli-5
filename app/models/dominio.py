"""Modelo unificado de domínios.

Após a migration 006, todas as tabelas de domínio (`dom_*`) foram
unificadas em `public.dominios`. Cada registro é identificado por
`(tipo, valor)`:

- `tipo='perfil_usuario'` → valores: admin, coordenador, autor
- `tipo='status_relatorio'` → valores: em_producao, em_revisao, finalizado, cancelado
- `tipo='status_envio'` → valores: pendente, processando, concluido, erro
- `tipo='status_revisao'` → valores: pendente, aprovada, rejeitada
- ... etc.

As FKs que antes apontavam para `dom_perfis_usuario.id` e
`dom_status_relatorios.id` agora apontam para `dominios.id_dominio`.
"""
from app import db
from app.models.mixins import AuditoriaMixin


class Dominio(db.Model, AuditoriaMixin):
    """Tabela genérica de domínios. Cada (tipo, valor) é único.

    Campos `ordem` e `nivel_acesso` são opcionais e usados conforme
    o tipo do domínio (ordem para listas, nivel_acesso para perfis).
    """
    __tablename__ = 'dominios'

    id_dominio = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False, index=True)
    valor = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    ordem = db.Column(db.Integer, default=0)
    nivel_acesso = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.UniqueConstraint('tipo', 'valor', name='uq_dominio_tipo_valor'),
    )

    # ------------------------------------------------------------------
    # Helpers (migram a API antiga `DomPerfilUsuario.query.filter_by(codigo=...)`
    # e `DomStatusRelatorio.query.filter_by(codigo=...)` para o tipo unificado).
    # ------------------------------------------------------------------

    @classmethod
    def por_codigo(cls, tipo, codigo):
        """Atalho: retorna o domínio (tipo, valor=codigo) ou None."""
        return cls.query.filter_by(tipo=tipo, valor=codigo).first()

    @classmethod
    def perfil_por_codigo(cls, codigo):
        """Atalho específico para perfil de usuário."""
        return cls.por_codigo('perfil_usuario', codigo)

    @classmethod
    def status_relatorio_por_codigo(cls, codigo):
        """Atalho específico para status de relatório."""
        return cls.por_codigo('status_relatorio', codigo)

    # Compatibilidade com APIs antigas que liam `.codigo` e `.id`.
    @property
    def codigo(self):
        return self.valor

    @property
    def id(self):
        return self.id_dominio
