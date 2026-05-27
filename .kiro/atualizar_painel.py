#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Atualização do Painel de Progresso
Lê tasks.md e regenera painel_progresso.html com dados atualizados
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class AnalisadorTasks:
    """Analisa arquivos tasks.md e extrai status das tasks"""
    
    def __init__(self, arquivo_tasks: str):
        self.arquivo = Path(arquivo_tasks)
        self.conteudo = self.arquivo.read_text(encoding='utf-8')
        self.tasks = []
        
    def analisar(self) -> Dict:
        """Analisa arquivo e retorna estatísticas"""
        self._extrair_tasks()
        return self._consolidar_stats()
    
    def _extrair_tasks(self):
        """Extrai todas as tasks com seu status"""
        # Padrão: [x] ou [ ] seguido de número e título
        padrao = r'- \[([x ])\]\*? (\d+\.\d+) (.+?)(?:\n|$)'
        
        matches = re.finditer(padrao, self.conteudo)
        for match in matches:
            status = '✅' if match.group(1) == 'x' else '⏳'
            numero = match.group(2)
            titulo = match.group(3).strip()
            
            self.tasks.append({
                'numero': numero,
                'titulo': titulo,
                'status': status,
                'arquivo': self.arquivo.name
            })
    
    def _consolidar_stats(self) -> Dict:
        """Consolida estatísticas de tasks"""
        total = len(self.tasks)
        completas = sum(1 for t in self.tasks if t['status'] == '✅')
        pendentes = total - completas
        
        # Agrupar por sprint/fase
        sprints = {}
        for task in self.tasks:
            sprint = task['numero'].split('.')[0]
            if sprint not in sprints:
                sprints[sprint] = {'completas': 0, 'pendentes': 0, 'tasks': []}
            
            if task['status'] == '✅':
                sprints[sprint]['completas'] += 1
            else:
                sprints[sprint]['pendentes'] += 1
            
            sprints[sprint]['tasks'].append(task)
        
        return {
            'total': total,
            'completas': completas,
            'pendentes': pendentes,
            'taxa_conclusao': round((completas / total * 100) if total > 0 else 0, 1),
            'sprints': sprints,
            'tasks': self.tasks
        }


def gerar_html(spec1_stats: Dict, spec2_stats: Dict) -> str:
    """Gera HTML do painel com dados atualizados"""
    
    total_geral = spec1_stats['total'] + spec2_stats['total']
    completas_geral = spec1_stats['completas'] + spec2_stats['completas']
    pendentes_geral = spec1_stats['pendentes'] + spec2_stats['pendentes']
    taxa_geral = round((completas_geral / total_geral * 100) if total_geral > 0 else 0, 1)
    
    # Preparar dados para gráficos
    sprint_labels = []
    sprint_completas = []
    sprint_pendentes = []
    
    for sprint in sorted(spec1_stats['sprints'].keys()):
        sprint_labels.append(f"Sprint {sprint}")
        sprint_completas.append(spec1_stats['sprints'][sprint]['completas'])
        sprint_pendentes.append(spec1_stats['sprints'][sprint]['pendentes'])
    
    fase_labels = []
    fase_tasks = []
    
    for fase in sorted(spec2_stats['sprints'].keys()):
        fase_labels.append(f"Fase {fase}")
        fase_tasks.append(spec2_stats['sprints'][fase]['completas'] + spec2_stats['sprints'][fase]['pendentes'])
    
    # Gerar linhas de tasks
    spec1_tasks_html = _gerar_linhas_tasks(spec1_stats['tasks'][:5])  # Top 5
    spec2_tasks_html = _gerar_linhas_tasks(spec2_stats['tasks'][:5])  # Top 5
    
    # Gerar linhas da tabela de dependências
    tabela_deps_html = _gerar_tabela_dependencias(spec1_stats, spec2_stats)
    
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Painel de Progresso - SRA PLI-5</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2em;
        }}

        .subtitle {{
            color: #666;
            font-size: 1em;
        }}

        .update-info {{
            background: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 10px 15px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 0.85em;
            color: #2c3e50;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }}

        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}

        .stat-label {{
            color: #999;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-complete {{ color: #27ae60; }}
        .stat-pending {{ color: #e74c3c; }}
        .stat-progress {{ color: #f39c12; }}
        .stat-total {{ color: #3498db; }}

        .progress-bar-container {{
            background: #ecf0f1;
            height: 10px;
            border-radius: 5px;
            overflow: hidden;
            margin-top: 15px;
        }}

        .progress-bar {{
            height: 100%;
            background: linear-gradient(90deg, #27ae60, #2ecc71);
            transition: width 0.3s ease;
            border-radius: 5px;
        }}

        .specs-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}

        .spec-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}

        .spec-header {{
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        .spec-title {{
            font-size: 1.3em;
            margin-bottom: 5px;
        }}

        .spec-status {{
            font-size: 0.9em;
            opacity: 0.9;
        }}

        .spec-content {{
            padding: 20px;
        }}

        .sprint-info {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
            font-size: 0.9em;
        }}

        .sprint-item {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }}

        .sprint-item strong {{
            color: #667eea;
        }}

        .task-list {{
            margin-top: 20px;
        }}

        .task-item {{
            display: flex;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #ecf0f1;
            font-size: 0.9em;
        }}

        .task-item:last-child {{
            border-bottom: none;
        }}

        .task-status {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            margin-right: 12px;
            font-weight: bold;
            font-size: 1.2em;
        }}

        .task-complete {{ background: #d4edda; color: #27ae60; }}
        .task-pending {{ background: #f8d7da; color: #e74c3c; }}

        .task-content {{
            flex: 1;
        }}

        .task-number {{
            font-weight: bold;
            color: #667eea;
            margin-right: 5px;
        }}

        .task-name {{
            color: #333;
        }}

        .chart-container {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}

        .chart-title {{
            font-size: 1.3em;
            margin-bottom: 20px;
            color: #333;
        }}

        .table-section {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #ecf0f1;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .badge-complete {{
            background: #d4edda;
            color: #27ae60;
        }}

        .badge-pending {{
            background: #f8d7da;
            color: #e74c3c;
        }}

        .legend {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .legend-symbol {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.8em;
        }}

        .legend-complete {{
            background: #27ae60;
            color: white;
        }}

        .legend-pending {{
            background: #e74c3c;
            color: white;
        }}

        footer {{
            text-align: center;
            color: white;
            padding: 20px;
            font-size: 0.9em;
        }}

        .section-title {{
            font-size: 1.5em;
            color: white;
            margin: 40px 0 20px 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}

        @media (max-width: 768px) {{
            .specs-section {{
                grid-template-columns: 1fr;
            }}

            .stat-grid {{
                grid-template-columns: 1fr;
            }}

            .sprint-info {{
                grid-template-columns: 1fr;
            }}

            h1 {{
                font-size: 1.5em;
            }}

            .stat-number {{
                font-size: 2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <h1>📊 Painel de Progresso - SRA PLI-5</h1>
            <p class="subtitle">Automação de Montagem de Relatórios & Integração de Capítulos-Seções</p>
            <div class="update-info">
                ⏰ Última atualização: {datetime.now().strftime('%d de %B de %Y às %H:%M:%S')} | 
                📁 Gerado automaticamente pelos tasks.md
            </div>
        </header>

        <!-- Statistics Cards -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total de Tasks</div>
                <div class="stat-number stat-total">{total_geral}</div>
                <div class="stat-label" style="margin-top: 10px;">distribuídas em 2 specs</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">Concluídas</div>
                <div class="stat-number stat-complete">{completas_geral}</div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {taxa_geral}%"></div>
                </div>
                <div class="stat-label" style="margin-top: 10px;">{taxa_geral}% de conclusão</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">Em Progresso</div>
                <div class="stat-number stat-progress">0</div>
                <div class="stat-label" style="margin-top: 15px; color: #666;">Aguardando inicialização</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">Pendentes</div>
                <div class="stat-number stat-pending">{pendentes_geral}</div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="background: linear-gradient(90deg, #e74c3c, #c0392b); width: {100-taxa_geral}%"></div>
                </div>
                <div class="stat-label" style="margin-top: 10px;">{100-taxa_geral}% restante</div>
            </div>
        </div>

        <h2 class="section-title">🎯 Specs por Status</h2>

        <!-- Specs Section -->
        <div class="specs-section">
            <!-- Spec 1 -->
            <div class="spec-card">
                <div class="spec-header">
                    <div class="spec-title">✨ Automação de Montagem</div>
                    <div class="spec-status">Tasks: {spec1_stats['completas']}/{spec1_stats['total']} concluídas</div>
                </div>
                <div class="spec-content">
                    <div class="sprint-info">
                        <div class="sprint-item">
                            <strong>Total:</strong> {spec1_stats['total']} tasks
                        </div>
                        <div class="sprint-item">
                            <strong>Completas:</strong> {spec1_stats['completas']} ✅
                        </div>
                        <div class="sprint-item">
                            <strong>Taxa:</strong> {spec1_stats['taxa_conclusao']}%
                        </div>
                        <div class="sprint-item">
                            <strong>Pendentes:</strong> {spec1_stats['pendentes']} ⏳
                        </div>
                    </div>
                    
                    <div class="task-list">
                        {spec1_tasks_html}
                    </div>
                </div>
            </div>

            <!-- Spec 2 -->
            <div class="spec-card">
                <div class="spec-header" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                    <div class="spec-title">🔧 Integração Capítulos-Seções</div>
                    <div class="spec-status">Tasks: {spec2_stats['completas']}/{spec2_stats['total']} concluídas</div>
                </div>
                <div class="spec-content">
                    <div class="sprint-info">
                        <div class="sprint-item" style="border-left-color: #f5576c;">
                            <strong>Total:</strong> {spec2_stats['total']} tasks
                        </div>
                        <div class="sprint-item" style="border-left-color: #f5576c;">
                            <strong>Completas:</strong> {spec2_stats['completas']} ❌
                        </div>
                        <div class="sprint-item" style="border-left-color: #f5576c;">
                            <strong>Taxa:</strong> {spec2_stats['taxa_conclusao']}%
                        </div>
                        <div class="sprint-item" style="border-left-color: #f5576c;">
                            <strong>Horas Est.:</strong> 73h
                        </div>
                    </div>
                    
                    <div class="task-list">
                        {spec2_tasks_html}
                    </div>
                </div>
            </div>
        </div>

        <h2 class="section-title">📈 Gráficos de Progresso</h2>

        <!-- Charts -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 30px; margin-bottom: 30px;">
            <div class="chart-container">
                <div class="chart-title">Distribuição por Spec</div>
                <canvas id="specChart"></canvas>
            </div>

            <div class="chart-container">
                <div class="chart-title">Status de Execução</div>
                <canvas id="statusChart"></canvas>
            </div>

            <div class="chart-container">
                <div class="chart-title">Sprints - Spec 1</div>
                <canvas id="sprintChart"></canvas>
            </div>

            <div class="chart-container">
                <div class="chart-title">Fases - Spec 2</div>
                <canvas id="faseChart"></canvas>
            </div>
        </div>

        <h2 class="section-title">📋 Matriz de Dependências</h2>

        <!-- Table -->
        <div class="table-section">
            <table>
                <thead>
                    <tr>
                        <th>Spec</th>
                        <th>Sprint/Fase</th>
                        <th>Status</th>
                        <th>Tarefas</th>
                        <th>Bloqueador</th>
                    </tr>
                </thead>
                <tbody>
                    {tabela_deps_html}
                </tbody>
            </table>

            <div class="legend">
                <div class="legend-item">
                    <div class="legend-symbol legend-complete">✓</div>
                    <span><strong>Concluído:</strong> Implementado e validado</span>
                </div>
                <div class="legend-item">
                    <div class="legend-symbol legend-pending">⏳</div>
                    <span><strong>Pendente/Bloqueado:</strong> Aguardando dependências</span>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <footer>
            <p>📊 Painel de Progresso - SRA PLI-5</p>
            <p>Para atualizar: execute <code>python .kiro/atualizar_painel.py</code></p>
        </footer>
    </div>

    <!-- Scripts -->
    <script>
        // Spec Chart
        new Chart(document.getElementById('specChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Automação ({spec1_stats['total']})', 'Integração ({spec2_stats['total']})'],
                datasets: [{{
                    data: [{spec1_stats['total']}, {spec2_stats['total']}],
                    backgroundColor: ['#667eea', '#f5576c'],
                    borderColor: ['#667eea', '#f5576c'],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});

        // Status Chart
        new Chart(document.getElementById('statusChart'), {{
            type: 'bar',
            data: {{
                labels: ['Concluídas', 'Pendentes'],
                datasets: [{{
                    label: 'Quantidade de Tasks',
                    data: [{completas_geral}, {pendentes_geral}],
                    backgroundColor: ['#27ae60', '#e74c3c'],
                    borderColor: ['#27ae60', '#e74c3c'],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{ beginAtZero: true }}
                }}
            }}
        }});

        // Sprint Chart
        new Chart(document.getElementById('sprintChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(sprint_labels)},
                datasets: [
                    {{
                        label: 'Completas',
                        data: {json.dumps(sprint_completas)},
                        backgroundColor: '#27ae60'
                    }},
                    {{
                        label: 'Pendentes',
                        data: {json.dumps(sprint_pendentes)},
                        backgroundColor: '#e74c3c'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                stacked: true,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});

        // Fase Chart
        new Chart(document.getElementById('faseChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(fase_labels)},
                datasets: [{{
                    label: 'Tasks por Fase',
                    data: {json.dumps(fase_tasks)},
                    backgroundColor: '#667eea'
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{ beginAtZero: true }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    return html


def _gerar_linhas_tasks(tasks: List) -> str:
    """Gera HTML das linhas de tasks"""
    html = ""
    for task in tasks:
        status_class = "task-complete" if task['status'] == '✅' else "task-pending"
        status_icon = "✓" if task['status'] == '✅' else "⏳"
        html += f"""
                        <div class="task-item">
                            <div class="task-status {status_class}">{status_icon}</div>
                            <span><span class="task-number">{task['numero']}:</span> <span class="task-name">{task['titulo']}</span></span>
                        </div>
"""
    return html


def _gerar_tabela_dependencias(spec1: Dict, spec2: Dict) -> str:
    """Gera linhas da tabela de dependências"""
    html = ""
    
    # Spec 1 - Sprints
    for sprint in sorted(spec1['sprints'].keys()):
        total = spec1['sprints'][sprint]['completas'] + spec1['sprints'][sprint]['pendentes']
        completas = spec1['sprints'][sprint]['completas']
        status_badge = f'<span class="badge badge-complete">✓ {completas}/{total}</span>' if completas == total else f'<span class="badge badge-pending">⏳ {completas}/{total}</span>'
        blocker = "—" if sprint == "1" else f"Sprint {int(sprint)-1}"
        
        html += f"""
                    <tr>
                        <td><strong>Automação</strong></td>
                        <td>Sprint {sprint}</td>
                        <td>{status_badge}</td>
                        <td>{completas}/{total}</td>
                        <td>{blocker}</td>
                    </tr>
"""
    
    # Spec 2 - Fases
    for fase in sorted(spec2['sprints'].keys()):
        total = spec2['sprints'][fase]['completas'] + spec2['sprints'][fase]['pendentes']
        completas = spec2['sprints'][fase]['completas']
        status_badge = f'<span class="badge badge-complete">✓ {completas}/{total}</span>' if completas == total else f'<span class="badge badge-pending">⏳ {completas}/{total}</span>'
        blocker = "Pode começar" if fase == "1" else f"Fase {int(fase)-1}"
        
        html += f"""
                    <tr style="background: #f8f9fa;">
                        <td><strong>Integração</strong></td>
                        <td>Fase {fase}</td>
                        <td>{status_badge}</td>
                        <td>{completas}/{total}</td>
                        <td>{blocker}</td>
                    </tr>
"""
    
    return html


def main():
    """Função principal"""
    print("📊 Atualizando Painel de Progresso...")
    
    # Caminhos
    base_path = Path(__file__).parent
    spec1_file = base_path / "specs" / "automacao-montagem-relatorios" / "tasks.md"
    spec2_file = base_path / "specs" / "integracao-capitulos-secoes" / "tasks.md"
    output_file = base_path / "painel_progresso.html"
    
    # Verificar arquivos
    if not spec1_file.exists():
        print(f"❌ Arquivo não encontrado: {spec1_file}")
        return False
    
    if not spec2_file.exists():
        print(f"❌ Arquivo não encontrado: {spec2_file}")
        return False
    
    # Analisar tasks
    print(f"📖 Analisando Spec 1: {spec1_file.name}")
    analisador1 = AnalisadorTasks(str(spec1_file))
    stats1 = analisador1.analisar()
    print(f"   ✓ {stats1['total']} tasks (✅ {stats1['completas']} | ⏳ {stats1['pendentes']})")
    
    print(f"📖 Analisando Spec 2: {spec2_file.name}")
    analisador2 = AnalisadorTasks(str(spec2_file))
    stats2 = analisador2.analisar()
    print(f"   ✓ {stats2['total']} tasks (✅ {stats2['completas']} | ⏳ {stats2['pendentes']})")
    
    # Gerar HTML
    print(f"🎨 Gerando HTML...")
    html = gerar_html(stats1, stats2)
    
    # Salvar arquivo
    output_file.write_text(html, encoding='utf-8')
    print(f"✅ Painel atualizado: {output_file}")
    print(f"📊 Total: {stats1['total'] + stats2['total']} tasks | ✅ {stats1['completas'] + stats2['completas']} concluídas")
    
    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
