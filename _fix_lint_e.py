import io

p = 'app/services/servico_envio_autor.py'
s = io.open(p, encoding='utf-8', newline='').read()
nl = '\r\n'

old = (
    '        except (OSError, ValueError, RuntimeError) as e:' + nl +
    '            # Indiciação não deve bloquear a geração da versão sugerida' + nl +
    '            pass'
)
new = (
    '        except (OSError, ValueError, RuntimeError):' + nl +
    '            # Indiciação não deve bloquear a geração da versão sugerida' + nl +
    '            pass'
)

assert old in s, 'bloco antigo nao encontrado'
s2 = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s2)
print('OK removido variavel e nao usada.')
