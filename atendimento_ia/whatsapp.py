import logging
import os

import requests

TOKEN = os.environ["META_ACCESS_TOKEN"]
PHONE_NUMBER_ID = os.environ["META_PHONE_NUMBER_ID"]
VERSAO_API = os.environ.get("META_API_VERSAO", "v21.0")

_sessao = requests.Session()
_sessao.headers.update({"Authorization": f"Bearer {TOKEN}"})


def enviar_texto(telefone, texto):
    """Envia uma mensagem de texto livre. Nunca levanta exceção — falhas de rede ou da API
    são logadas, para que o chamador possa continuar (marcar lead quente, notificar, etc.)
    mesmo que o envio ao cliente não tenha funcionado."""
    url = f"https://graph.facebook.com/{VERSAO_API}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {"body": texto},
    }
    try:
        resposta = _sessao.post(url, json=payload, timeout=30)
    except requests.exceptions.RequestException:
        logging.exception("Falha de rede ao enviar mensagem para %s", telefone)
        return None
    if resposta.status_code != 200:
        logging.error("Falha ao enviar mensagem para %s: %s", telefone, resposta.text)
    return resposta
