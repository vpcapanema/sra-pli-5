# Produto — SRA · PLI-SP

## Visão geral

O **Sistema de Relatório de Atividades (SRA)** é uma aplicação web para produção, revisão e exportação de relatórios técnicos a partir de modelos DOCX. O sistema separa **conteúdo**, **estrutura** e **formatação** para preservar fidelidade visual e permitir edição controlada por múltiplos colaboradores.

## Domínio

Relatórios técnicos institucionais (PLI-SP) organizados em capítulos, com ciclo editorial colaborativo entre autores e coordenadores.

## Conceitos centrais

- **Modelo de relatório**: DOCX-base que define a estrutura canônica do documento (capítulos, estilos, seções OOXML).
- **Relatório de produção**: instância operacional do período vigente, editável.
- **Relatório finalizado**: versão aprovada e exportada ao fim do ciclo.
- **Capítulo de documento**: unidade editável atribuída a um autor.
- **Envio de conteúdo**: upload de DOCX pelo autor para um capítulo.
- **Biblioteca de formatação canônica**: repositório versionado dos parâmetros visuais extraídos do modelo.

## Perfis de usuário

- `admin` — gerencia usuários, modelos e configurações globais.
- `coordenador` — cria relatórios de produção, atribui responsáveis, aprova/reprova capítulos, finaliza e exporta.
- `autor` — edita capítulos atribuídos, faz upload de DOCX e finaliza para revisão.

## Estados de capítulo

`em_edicao` → `finalizado` (autor envia) → `aprovado` ou `reprovado` (coordenador) → se reprovado, volta para `em_edicao`.

## Idioma

Toda a interface, código (nomes de variáveis, classes, comentários, mensagens), documentação e dados de domínio estão em **português do Brasil**. Mantenha esse padrão em qualquer contribuição.
