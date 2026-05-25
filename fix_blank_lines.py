#!/usr/bin/env python
"""Script para corrigir blank lines no relatorio.py."""

with open('app/routes/relatorio.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Regras:
# 1. Entre funções de nível superior: exatamente 2 linhas em branco
# 2. Dentro de classes/funções: 1 linha em branco máximo
# 3. Antes de decorators @: exatamente 2 linhas em branco (se função de nível superior)

new_lines = []
for i, line in enumerate(lines):
    stripped = line.strip()

    if stripped.startswith('@relatorio_bp.route'):
        # Garantir 2 linhas em branco antes do decorator
        # Remover linhas em branco excessivas antes
        while len(new_lines) >= 1 and new_lines[-1].strip() == '' and len(new_lines) >= 2 and new_lines[-2].strip() == '':
            pass  # já tem 2, ok
        if len(new_lines) >= 1 and new_lines[-1].strip() == '':
            if len(new_lines) >= 2 and new_lines[-2].strip() != '':
                # Tem 1, precisa de mais 1
                new_lines.append('\n')
            elif len(new_lines) >= 2 and new_lines[-2].strip() == '':
                # Tem 2 ou mais, ok
                pass
        else:
            # Não tem nenhuma, adicionar 2
            new_lines.append('\n')
            new_lines.append('\n')
        new_lines.append(line)
    elif stripped.startswith('def ') and i > 0 and not lines[i-1].strip().startswith('@'):
        # Função sem decorator antes - garantir 2 linhas em branco
        if len(new_lines) >= 1 and new_lines[-1].strip() == '':
            if len(new_lines) >= 2 and new_lines[-2].strip() != '':
                new_lines.append('\n')
        else:
            new_lines.append('\n')
            new_lines.append('\n')
        new_lines.append(line)
    else:
        new_lines.append(line)

# Remover linhas em branco excessivas no final
while new_lines and new_lines[-1].strip() == '':
    new_lines.pop()

with open('app/routes/relatorio.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Blank lines corrigidas.')
