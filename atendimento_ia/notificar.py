import logging
import os

from whatsapp import enviar_texto

TELEFONE_ALEXANDRE = os.environ.get("TELEFONE_ALEXANDRE")


def notificar_alexandre(telefone_lead, nome_lead, historico):
    if not TELEFONE_ALEXANDRE:
        logging.warning("TELEFONE_ALEXANDRE não configurado — não foi possível notificar.")
        return
    resumo = "\n".join(f"{m['role']}: {m['texto']}" for m in historico[-6:])
    mensagem = (
        "🔥 Lead quente!\n"
        f"Nome: {nome_lead}\n"
        f"Telefone: {telefone_lead}\n\n"
        f"Últimas mensagens:\n{resumo}"
    )
    enviar_texto(TELEFONE_ALEXANDRE, mensagem)
