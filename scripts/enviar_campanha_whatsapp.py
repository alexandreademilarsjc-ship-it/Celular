#!/usr/bin/env python3
"""Envia mensagens de template do WhatsApp direto pela Meta Cloud API.

Substitui a integração via Redrive: lê uma lista de clientes de um arquivo
CSV/Excel, gera o texto das variáveis do template com a API da Anthropic e
envia cada mensagem com `requests` direto para a Graph API da Meta.

Exemplo:
    python enviar_campanha_whatsapp.py \\
        --arquivo clientes.xlsx \\
        --template boas_vindas \\
        --variavel "coluna:nome" \\
        --variavel "ia:Escreva uma saudação curta e calorosa para {nome}, cliente da loja {loja}, sobre a promoção de aniversário." \\
        --dry-run
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import anthropic
import pandas as pd
import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

LIMITE_CARACTERES_VARIAVEL = 1024


class ErroFatal(Exception):
    """Erro que interrompe o script inteiro (ex.: credencial inválida)."""


def carregar_planilha(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        sys.exit(f"Arquivo não encontrado: {caminho}")
    sufixo = caminho.suffix.lower()
    if sufixo == ".csv":
        return pd.read_csv(caminho, dtype=str).fillna("")
    if sufixo in (".xlsx", ".xls"):
        return pd.read_excel(caminho, dtype=str).fillna("")
    sys.exit(f"Formato de arquivo não suportado: {sufixo}. Use .csv ou .xlsx.")


def normalizar_telefone(numero, ddi_padrao):
    if numero is None:
        return None
    digitos = re.sub(r"\D", "", str(numero))
    if not digitos:
        return None
    digitos = digitos.lstrip("0")
    # Números brasileiros costumam vir sem DDI na planilha; completa com o
    # padrão quando o comprimento sugere que o DDI está ausente.
    if not digitos.startswith(ddi_padrao) and len(digitos) <= 11:
        digitos = f"{ddi_padrao}{digitos}"
    if not re.fullmatch(r"\d{10,15}", digitos):
        return None
    return digitos


def sanitizar_texto_parametro(texto, limite=LIMITE_CARACTERES_VARIAVEL):
    texto = re.sub(r"\s+", " ", str(texto)).strip()
    if len(texto) > limite:
        logging.warning("Texto de variável truncado para %d caracteres.", limite)
        texto = texto[:limite].rstrip()
    return texto


def analisar_especificacoes_variaveis(especificacoes):
    specs = []
    for item in especificacoes:
        tipo, separador, valor = item.partition(":")
        if not separador:
            raise ValueError(
                f"Variável inválida '{item}'. Use o formato 'coluna:NOME' ou 'ia:PROMPT'."
            )
        tipo = tipo.strip().lower()
        if tipo not in ("coluna", "ia"):
            raise ValueError(f"Tipo de variável inválido: '{tipo}'. Use 'coluna:' ou 'ia:'.")
        specs.append((tipo, valor))
    return specs


def gerar_texto_ia(client, modelo, prompt, max_tentativas=3):
    ultimo_erro = None
    for tentativa in range(1, max_tentativas + 1):
        try:
            resposta = client.messages.create(
                model=modelo,
                max_tokens=1024,
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(
                bloco.text for bloco in resposta.content if bloco.type == "text"
            ).strip()
        except anthropic.AuthenticationError as e:
            raise ErroFatal(
                "Chave da API Anthropic inválida ou ausente (ANTHROPIC_API_KEY)."
            ) from e
        except anthropic.RateLimitError as e:
            espera = int(e.response.headers.get("retry-after", "10"))
            logging.warning("Limite de taxa da Anthropic atingido, aguardando %ds...", espera)
            time.sleep(espera)
            ultimo_erro = e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500 and tentativa < max_tentativas:
                time.sleep(2 ** tentativa)
                ultimo_erro = e
                continue
            raise
        except anthropic.APIConnectionError as e:
            if tentativa < max_tentativas:
                time.sleep(2 ** tentativa)
                ultimo_erro = e
                continue
            raise
    raise RuntimeError(f"Falha ao gerar texto com a IA após {max_tentativas} tentativas: {ultimo_erro}")


def montar_parametros_linha(client, modelo, specs, linha):
    valores = []
    dados_linha = linha.to_dict()
    for tipo, valor in specs:
        if tipo == "coluna":
            if valor not in dados_linha:
                raise ValueError(f"Coluna '{valor}' não encontrada na planilha.")
            texto = dados_linha[valor]
        else:
            try:
                prompt = valor.format(**dados_linha)
            except KeyError as e:
                raise ValueError(f"Coluna referenciada no prompt não encontrada: {e}") from e
            texto = gerar_texto_ia(client, modelo, prompt)
        valores.append(sanitizar_texto_parametro(texto))
    return valores


def montar_payload(telefone, nome_template, idioma, parametros_texto):
    template = {"name": nome_template, "language": {"code": idioma}}
    if parametros_texto:
        template["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": texto} for texto in parametros_texto],
            }
        ]
    return {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "template",
        "template": template,
    }


def enviar_mensagem_whatsapp(sessao, url, payload, max_tentativas=3):
    ultima_resposta = None
    for tentativa in range(1, max_tentativas + 1):
        resposta = sessao.post(url, json=payload, timeout=30)
        ultima_resposta = resposta
        if resposta.status_code == 200:
            return resposta.json()
        if resposta.status_code in (401, 403):
            raise ErroFatal(
                f"Falha de autenticação na Meta Cloud API ({resposta.status_code}): {resposta.text}"
            )
        if resposta.status_code == 429 or resposta.status_code >= 500:
            espera = 2 ** tentativa
            logging.warning("Meta Cloud API retornou %d, aguardando %ds...", resposta.status_code, espera)
            time.sleep(espera)
            continue
        raise RuntimeError(f"Erro da Meta Cloud API ({resposta.status_code}): {resposta.text}")
    raise RuntimeError(
        f"Falha ao enviar mensagem após {max_tentativas} tentativas: "
        f"{ultima_resposta.text if ultima_resposta is not None else ''}"
    )


def analisar_argumentos():
    parser = argparse.ArgumentParser(
        description="Envia campanha de templates do WhatsApp via Meta Cloud API, "
        "com textos de variáveis gerados pela IA da Anthropic."
    )
    parser.add_argument("--arquivo", required=True, help="Caminho do arquivo CSV ou Excel com os clientes")
    parser.add_argument("--coluna-telefone", default="telefone", help="Coluna com o número de telefone (padrão: telefone)")
    parser.add_argument("--ddi-padrao", default="55", help="DDI usado quando o número não tem código do país (padrão: 55)")
    parser.add_argument("--template", required=True, help="Nome do template aprovado na Meta")
    parser.add_argument("--idioma", default="pt_BR", help="Código de idioma do template (padrão: pt_BR)")
    parser.add_argument(
        "--variavel",
        dest="variaveis",
        action="append",
        default=[],
        help="Variável do template na ordem em que aparece, no formato "
        "'coluna:NOME_DA_COLUNA' ou 'ia:PROMPT com {colunas} da planilha'. "
        "Pode ser repetido.",
    )
    parser.add_argument("--modelo", default="claude-opus-5", help="Modelo Anthropic para gerar os textos (padrão: claude-opus-5)")
    parser.add_argument("--versao-api", default="v21.0", help="Versão da Graph API da Meta (padrão: v21.0)")
    parser.add_argument("--saida", default="resultado_envio.csv", help="CSV de saída com o resultado de cada envio")
    parser.add_argument("--intervalo", type=float, default=1.0, help="Segundos de espera entre cada cliente (padrão: 1.0)")
    parser.add_argument("--limite", type=int, default=None, help="Processa só as N primeiras linhas (para testes)")
    parser.add_argument("--dry-run", action="store_true", help="Gera os textos e monta os payloads, mas não envia as mensagens")
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = analisar_argumentos()

    token = os.environ.get("META_ACCESS_TOKEN")
    phone_number_id = os.environ.get("META_PHONE_NUMBER_ID")
    if not args.dry_run and (not token or not phone_number_id):
        sys.exit(
            "Defina META_ACCESS_TOKEN e META_PHONE_NUMBER_ID (variáveis de ambiente "
            "ou arquivo .env) antes de enviar. Use --dry-run para testar sem essas credenciais."
        )

    try:
        specs = analisar_especificacoes_variaveis(args.variaveis)
    except ValueError as e:
        sys.exit(str(e))

    df = carregar_planilha(args.arquivo)
    if args.coluna_telefone not in df.columns:
        sys.exit(
            f"Coluna '{args.coluna_telefone}' não encontrada. "
            f"Colunas disponíveis: {list(df.columns)}"
        )
    if args.limite:
        df = df.head(args.limite)

    anthropic_client = anthropic.Anthropic()
    sessao = requests.Session()
    if not args.dry_run:
        sessao.headers.update({"Authorization": f"Bearer {token}"})
        url_envio = f"https://graph.facebook.com/{args.versao_api}/{phone_number_id}/messages"

    resultados = []
    total = len(df)
    for posicao, (_, linha) in enumerate(df.iterrows(), start=1):
        telefone_original = linha.get(args.coluna_telefone, "")
        telefone = normalizar_telefone(telefone_original, args.ddi_padrao)
        logging.info("[%d/%d] Processando %s", posicao, total, telefone_original)

        if not telefone:
            logging.warning("Telefone inválido, pulando: %s", telefone_original)
            resultados.append({"telefone": telefone_original, "status": "erro", "detalhe": "telefone inválido"})
            continue

        try:
            parametros = montar_parametros_linha(anthropic_client, args.modelo, specs, linha)
            payload = montar_payload(telefone, args.template, args.idioma, parametros)

            if args.dry_run:
                logging.info("[dry-run] Payload: %s", json.dumps(payload, ensure_ascii=False))
                resultados.append({"telefone": telefone, "status": "dry-run", "detalhe": json.dumps(parametros, ensure_ascii=False)})
            else:
                resposta = enviar_mensagem_whatsapp(sessao, url_envio, payload)
                message_id = resposta.get("messages", [{}])[0].get("id", "")
                resultados.append({"telefone": telefone, "status": "enviado", "detalhe": message_id})
        except ErroFatal as e:
            logging.error("Erro fatal, interrompendo o script: %s", e)
            pd.DataFrame(resultados).to_csv(args.saida, index=False)
            sys.exit(1)
        except Exception as e:
            logging.error("Falha ao processar %s: %s", telefone, e)
            resultados.append({"telefone": telefone, "status": "erro", "detalhe": str(e)})

        time.sleep(args.intervalo)

    pd.DataFrame(resultados).to_csv(args.saida, index=False)
    logging.info("Concluído. Resultado salvo em %s", args.saida)


if __name__ == "__main__":
    main()
