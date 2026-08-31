import hashlib
import hmac
import logging
import os

from fastapi import FastAPI, Request, Response

from armazenamento import (
    inicializar_banco,
    marcar_quente,
    obter_historico,
    obter_ou_criar_lead,
    salvar_mensagem,
)
from conversa import gerar_resposta
from notificar import notificar_alexandre
from whatsapp import enviar_texto

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

VERIFY_TOKEN = os.environ["WEBHOOK_VERIFY_TOKEN"]
APP_SECRET = os.environ.get("META_APP_SECRET")

inicializar_banco()
app = FastAPI()


@app.get("/webhook")
def verificar_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(status_code=403)


def assinatura_valida(corpo: bytes, assinatura_recebida) -> bool:
    if not APP_SECRET:
        logging.warning("META_APP_SECRET não configurado — pulando verificação de assinatura.")
        return True
    if not assinatura_recebida or not assinatura_recebida.startswith("sha256="):
        return False
    esperado = hmac.new(APP_SECRET.encode(), corpo, hashlib.sha256).hexdigest()
    recebido = assinatura_recebida.removeprefix("sha256=")
    return hmac.compare_digest(esperado, recebido)


@app.post("/webhook")
async def receber_webhook(request: Request):
    corpo = await request.body()
    if not assinatura_valida(corpo, request.headers.get("x-hub-signature-256")):
        return Response(status_code=403)

    payload = await request.json()
    for entrada in payload.get("entry", []):
        for mudanca in entrada.get("changes", []):
            valor = mudanca.get("value", {})
            for mensagem in valor.get("messages", []):
                try:
                    processar_mensagem(mensagem, valor)
                except Exception:
                    logging.exception("Falha ao processar mensagem de %s", mensagem.get("from"))
    return {"status": "ok"}


def processar_mensagem(mensagem, valor):
    telefone = mensagem.get("from")
    if not telefone or mensagem.get("type") != "text":
        logging.info("Mensagem ignorada (tipo não suportado: %s)", mensagem.get("type"))
        return

    texto_recebido = mensagem["text"]["body"]
    nome = None
    for contato in valor.get("contacts", []):
        if contato.get("wa_id") == telefone:
            nome = contato.get("profile", {}).get("name")

    lead = obter_ou_criar_lead(telefone, nome)
    salvar_mensagem(telefone, "user", texto_recebido)
    historico = obter_historico(telefone)

    resultado = gerar_resposta(historico)
    salvar_mensagem(telefone, "assistant", resultado["resposta"])
    enviar_texto(telefone, resultado["resposta"])

    if resultado["quer_falar_com_humano"] and not lead["quente"]:
        marcar_quente(telefone)
        notificar_alexandre(telefone, nome or telefone, obter_historico(telefone))
