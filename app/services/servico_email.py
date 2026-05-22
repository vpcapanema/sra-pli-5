import json
import urllib.request
import urllib.error
from flask import current_app

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'


class ServicoEmail:

    @staticmethod
    def _corpo_convite(nome, link):
        return f"""
        <div style="font-family:sans-serif;max-width:480px;
                    margin:0 auto;padding:24px;">
            <h2 style="color:#1a5632;">SRA · PLI-SP</h2>
            <p>Olá <strong>{nome}</strong>,</p>
            <p>Você foi convidado(a) para acessar o
            Sistema de Relatórios de Atividades.</p>
            <p>Clique no botão abaixo para definir sua
            senha e ativar sua conta:</p>
            <p style="text-align:center;margin:32px 0;">
                <a href="{link}"
                   style="background:#1a5632;color:#fff;
                          padding:12px 32px;
                          border-radius:6px;
                          text-decoration:none;
                          font-weight:bold;">
                    Ativar minha conta
                </a>
            </p>
            <p style="font-size:12px;color:#666;">
                Se o botão não funcionar, copie e cole
                este link no navegador:<br>
                <a href="{link}">{link}</a>
            </p>
            <p style="font-size:12px;color:#999;">
                Este convite expira em 72 horas.
            </p>
        </div>
        """

    @staticmethod
    def _enviar_brevo(api_key, remetente_email,
                      remetente_nome, destinatario,
                      assunto, corpo_html):
        payload = json.dumps({
            'sender': {
                'name': remetente_nome,
                'email': remetente_email,
            },
            'to': [{'email': destinatario}],
            'subject': assunto,
            'htmlContent': corpo_html,
        }).encode('utf-8')

        req = urllib.request.Request(
            BREVO_API_URL,
            data=payload,
            headers={
                'api-key': api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            method='POST',
        )

        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(
            resp.read().decode('utf-8')
        )

    @staticmethod
    def enviar_convite(destinatario, nome, token):
        cfg = current_app.config
        base_url = cfg['APP_BASE_URL']
        link = f"{base_url}/ativar-conta/{token}"

        api_key = cfg.get('BREVO_API_KEY', '')
        if not api_key:
            current_app.logger.warning(
                'BREVO_API_KEY não configurada. '
                f'Link de convite: {link}'
            )
            return link

        assunto = 'SRA · PLI-SP — Convite para acesso'
        corpo = ServicoEmail._corpo_convite(nome, link)

        try:
            status, body = ServicoEmail._enviar_brevo(
                api_key,
                cfg.get('BREVO_FROM_EMAIL'),
                cfg.get('BREVO_FROM_NAME'),
                destinatario,
                assunto,
                corpo,
            )
            current_app.logger.info(
                f'Convite enviado para {destinatario} '
                f'(status {status}, id {body})'
            )
        except urllib.error.HTTPError as e:
            current_app.logger.error(
                f'Erro ao enviar e-mail para '
                f'{destinatario}: {e.code} '
                f'{e.read().decode()}'
            )
        except Exception as e:
            current_app.logger.error(
                f'Erro ao enviar e-mail para '
                f'{destinatario}: {e}'
            )

        return link

    @staticmethod
    def _corpo_recuperacao(nome, link):
        return f"""
        <div style="font-family:sans-serif;max-width:480px;
                    margin:0 auto;padding:24px;">
            <h2 style="color:#1a5632;">SRA · PLI-SP</h2>
            <p>Olá <strong>{nome}</strong>,</p>
            <p>Recebemos uma solicitação para redefinir
            sua senha no Sistema de Relatórios de
            Atividades.</p>
            <p>Clique no botão abaixo para criar uma
            nova senha:</p>
            <p style="text-align:center;margin:32px 0;">
                <a href="{link}"
                   style="background:#1a5632;color:#fff;
                          padding:12px 32px;
                          border-radius:6px;
                          text-decoration:none;
                          font-weight:bold;">
                    Redefinir minha senha
                </a>
            </p>
            <p style="font-size:12px;color:#666;">
                Se o botão não funcionar, copie e cole
                este link no navegador:<br>
                <a href="{link}">{link}</a>
            </p>
            <p style="font-size:12px;color:#999;">
                Este link expira em 1 hora. Se você não
                solicitou essa alteração, ignore este
                e-mail.
            </p>
        </div>
        """

    @staticmethod
    def enviar_recuperacao(destinatario, nome, token):
        cfg = current_app.config
        base_url = cfg['APP_BASE_URL']
        link = f"{base_url}/redefinir-senha/{token}"

        api_key = cfg.get('BREVO_API_KEY', '')
        if not api_key:
            current_app.logger.warning(
                'BREVO_API_KEY não configurada. '
                f'Link de recuperação: {link}'
            )
            return link

        assunto = 'SRA · PLI-SP — Redefinição de senha'
        corpo = ServicoEmail._corpo_recuperacao(
            nome, link
        )

        try:
            status, body = ServicoEmail._enviar_brevo(
                api_key,
                cfg.get('BREVO_FROM_EMAIL'),
                cfg.get('BREVO_FROM_NAME'),
                destinatario,
                assunto,
                corpo,
            )
            current_app.logger.info(
                f'Recuperação enviada para '
                f'{destinatario} '
                f'(status {status}, id {body})'
            )
        except urllib.error.HTTPError as e:
            current_app.logger.error(
                f'Erro ao enviar e-mail para '
                f'{destinatario}: {e.code} '
                f'{e.read().decode()}'
            )
        except Exception as e:
            current_app.logger.error(
                f'Erro ao enviar e-mail para '
                f'{destinatario}: {e}'
            )

        return link
