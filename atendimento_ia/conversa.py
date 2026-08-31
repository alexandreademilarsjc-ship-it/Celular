import json
import os

import anthropic

client = anthropic.Anthropic()
MODELO = os.environ.get("MODELO_IA", "claude-opus-5")

# TODO: preencher com os detalhes reais da oferta (condições de entrada,
# valor da carta de crédito, prazos, diferenciais) antes de usar em produção.
SYSTEM_PROMPT = """Você é um SDR (Sales Development Representative) falando em nome do Alexandre \
pelo WhatsApp, sobre uma oportunidade de consórcio de imóvel.

O cliente já aceitou receber uma mensagem sua (respondeu "sim" ou algo do tipo a um primeiro \
contato). Seu objetivo é conversar naturalmente, entender o interesse dele e, se fizer sentido, \
conectar com o Alexandre.

SOBRE A OFERTA (preencher com os detalhes reais da empresa):
- [TODO: condições de entrada, valor da carta de crédito, prazos, diferenciais]

REGRAS DE CONVERSA:
- Seja direto, cordial e natural, como uma pessoa real conversando pelo WhatsApp (frases curtas, \
sem forçar emoji em excesso, sem parecer um robô).
- Nunca minta sobre o produto nem prometa condições que não foram informadas acima.
- Se o cliente perguntar "sobre o que é" ou similar, explique que é sobre uma oportunidade de \
consórcio de imóvel com condições especiais.
- Se o cliente demonstrar interesse real ou pedir para falar com alguém/com o Alexandre, confirme \
que você vai conectar os dois e marque quer_falar_com_humano como true.
- Se o cliente disser claramente que não tem interesse ou pedir para não receber mais mensagens, \
respeite, encerre educadamente e marque quer_falar_com_humano como false.
"""

ESQUEMA_RESPOSTA = {
    "type": "object",
    "properties": {
        "resposta": {
            "type": "string",
            "description": "Texto a ser enviado ao cliente pelo WhatsApp",
        },
        "quer_falar_com_humano": {
            "type": "boolean",
            "description": (
                "true se o cliente pediu para falar com o Alexandre/um representante ou "
                "demonstrou interesse claro em avançar"
            ),
        },
    },
    "required": ["resposta", "quer_falar_com_humano"],
    "additionalProperties": False,
}


def gerar_resposta(historico):
    mensagens = [{"role": item["role"], "content": item["texto"]} for item in historico]
    resposta = client.messages.create(
        model=MODELO,
        max_tokens=1024,
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": ESQUEMA_RESPOSTA},
        },
        system=SYSTEM_PROMPT,
        messages=mensagens,
    )
    texto = next(bloco.text for bloco in resposta.content if bloco.type == "text")
    return json.loads(texto)
