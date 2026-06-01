from pathlib import Path
import re

path = Path("app/templates/editor_autor.html")
text = path.read_text(encoding="utf-8")

pattern = r'''        <div class="ea__panel ea__panel--upload">.*?        </div>\r?\n    </section>'''

replacement = """        <div class=\"ea__panel ea__panel--upload\">
            <div class=\"ea__panel-head\">
                <span class=\"ea__panel-icon\">
                    <i class=\"ph ph-upload-simple\"></i>
                </span>
                <div>
                    <h2 class=\"ea__panel-title\">Envio de conteúdo</h2>
                    <p class=\"ea__panel-subtitle\">
                        Envie um DOCX para substituir o conteúdo do capítulo selecionado.
                    </p>
                </div>
            </div>

            {% if capitulo_selecionado and (perfil_ativo in ('coordenador', 'admin') or capitulo_selecionado.id_usuario_responsavel == current_user.id) %}
            <div class=\"ea__upload-stack\">
                <section class=\"ea__upload-card\">
                    <div class=\"ea__upload-card-head\">
                        <div>
                            <p class=\"ea__upload-kicker\">Capítulo selecionado</p>
                            <h3 class=\"ea__upload-title\">
                                {{ capitulo_selecionado.indice_capitulo or '—' }} {{ capitulo_selecionado.titulo_capitulo }}
                            </h3>
                        </div>

                        <div class=\"ea__upload-badges\">
                            {% if capitulo_selecionado.id_capitulo_documento in capitulos_do_autor_ids %}
                            <span class=\"ea__cap-badge ea__cap-badge--meu\" title=\"Você é responsável por este capítulo\">
                                <i class=\"ph-fill ph-star\"></i> MEU
                            </span>
                            {% else %}
                            <span class=\"ea__cap-badge ea__cap-badge--coord\" title=\"Acesso de coordenação\">
                                <i class=\"ph ph-shield-check\"></i> COORD
                            </span>
                            {% endif %}
                        </div>
                    </div>

                    <div class=\"ea__upload-meta\">
                        <span><strong>Status:</strong> {{ capitulo_selecionado.descricao_status }}</span>
                        <span><strong>Responsável:</strong> {{ current_user.nome or current_user.email }}</span>
                    </div>
                </section>

                <section class=\"ea__upload-card\">
                    <div class=\"ea__upload-card-head\">
                        <div>
                            <p class=\"ea__upload-kicker\">Arquivo DOCX</p>
                            <h3 class=\"ea__upload-title\">Enviar novo conteúdo</h3>
                        </div>
                    </div>

                    <form class=\"ea__upload-form\"
                          method=\"POST\"
                          enctype=\"multipart/form-data\"
                          action=\"{{ url_for('relatorio.upload_conteudo', id_versao=versao.id, id_capitulo=capitulo_selecionado.id_capitulo_documento) }}\">
                        <input type=\"hidden\" name=\"csrf_token\" value=\"{{ csrf_token() }}\">

                        <div class=\"ea__upload-field\">
                            <label class=\"ea__upload-label\" for=\"arquivo_docx_{{ capitulo_selecionado.id_capitulo_documento }}\">
                                Arquivo DOCX
                            </label>
                            <input class=\"ea__upload-input\"
                                   type=\"file\"
                                   id=\"arquivo_docx_{{ capitulo_selecionado.id_capitulo_documento }}\"
                                   name=\"arquivo_docx\"
                                   accept=\".docx\"
                                   required>
                            <p class=\"ea__upload-help\">
                                O arquivo deve ser .docx e vai substituir o conteúdo do capítulo selecionado.
                            </p>
                        </div>

                        <div class=\"ea__buttons-row\">
                            <button type=\"submit\" class=\"ea__primary-btn\">
                                <i class=\"ph ph-file-arrow-up\"></i>
                                Enviar arquivo
                            </button>
                        </div>
                    </form>
                </section>

                {% if envio_pendente %}
                <section class=\"ea__upload-card ea__upload-card--status\">
                    <div class=\"ea__upload-card-head\">
                        <div>
                            <p class=\"ea__upload-kicker\">Envio pendente</p>
                            <h3 class=\"ea__upload-title\">Último arquivo recebido</h3>
                        </div>
                    </div>

                    <div class=\"ea__upload-status\">
                        <p>
                            Arquivo enviado:
                            <strong>{{ envio_pendente.nome_arquivo }}</strong>
                        </p>
                        <p>
                            Situação:
                            <span class=\"sra-badge sra-badge--{{ envio_pendente.status_envio }}\">
                                {{ envio_pendente.status_envio | replace('_', ' ') | capitalize }}
                            </span>
                        </p>
                    </div>

                    <div class=\"ea__upload-actions\">
                        <form method=\"POST\"
                              action=\"{{ url_for('relatorio.confirmar_envio', id_envio=envio_pendente.id_envio_conteudo, acao='importar') }}\">
                            <input type=\"hidden\" name=\"csrf_token\" value=\"{{ csrf_token() }}\">
                            <button type=\"submit\" class=\"ea__primary-btn\">
                                <i class=\"ph ph-check\"></i>
                                Importar conteúdo
                            </button>
                        </form>

                        <form method=\"POST\"
                              action=\"{{ url_for('relatorio.confirmar_envio', id_envio=envio_pendente.id_envio_conteudo, acao='rejeitar') }}\">
                            <input type=\"hidden\" name=\"csrf_token\" value=\"{{ csrf_token() }}\">
                            <button type=\"submit\" class=\"ea__secondary-btn\">
                                <i class=\"ph ph-x\"></i>
                                Rejeitar e reenviar
                            </button>
                        </form>
                    </div>

                    <p class=\"ea__upload-help\">
                        A prévia completa continua disponível no fluxo de upload do capítulo.
                    </p>
                </section>
                {% endif %}
            </div>
            {% else %}
            <div class=\"ea__upload-empty\">
                <i class=\"ph ph-warning-circle\"></i>
                <p>
                    Selecione um capítulo acima para habilitar o envio de conteúdo.
                </p>
            </div>
            {% endif %}
        </div>
    </section>"""

updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
if count != 1:
    raise RuntimeError(f"Não foi possível localizar o bloco de upload para substituir. Ocorrências: {count}")

path.write_text(updated, encoding="utf-8", newline="\n")
print("OK: bloco de upload substituído.")
