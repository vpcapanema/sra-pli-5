from app import create_app

app = create_app()
with app.app_context():
    from app.models.envio_conteudo import EnvioConteudo
    envio = EnvioConteudo.query.get(2)
    if envio:
        print(f'Envio ID: {envio.id_envio_conteudo}')
        print(f'sugestoes_json: {envio.sugestoes_json}')
    else:
        print('Envio ID 2 não encontrado')
