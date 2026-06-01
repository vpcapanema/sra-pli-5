from pathlib import Path

path = Path("app/templates/editor_autor.html")
text = path.read_text(encoding="utf-8")

old_open = "<div class=\"ea\">\n"
new_open = "<div class=\"ea\">\n    <div class=\"ea__content\">\n"

old_close = (
    "</div>\n\n{# Dados PRÓPRIOS do editor do autor — IDs únicos #}\n"
)

new_close = (
    "    </div>\n</div>\n\n{# Dados PRÓPRIOS do editor do autor — IDs únicos #}\n"
)

if old_open not in text:
    raise RuntimeError("Não encontrei a abertura esperada da estrutura .ea")

text = text.replace(old_open, new_open, 1)

if old_close not in text:
    raise RuntimeError("Não encontrei o fechamento esperado antes dos dados do editor")

text = text.replace(old_close, new_close, 1)

path.write_text(text, encoding="utf-8", newline="\n")
print("OK: estrutura .ea__content aplicada.")
