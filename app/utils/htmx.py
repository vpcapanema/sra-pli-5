from flask import request, render_template


def render_conteudo(componentes, **kwargs):
    """Renderiza página completa ou apenas o conteúdo parcial se for requisição HTMX."""
    if request.headers.get('HX-Request'):
        return render_template(
            'parcial.html',
            componentes=componentes,
            **kwargs
        )
    return render_template(
        'principal.html',
        componentes=componentes,
        **kwargs
    )
