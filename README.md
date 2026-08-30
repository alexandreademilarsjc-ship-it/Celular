# Celular

## Envio de campanha WhatsApp direto pela Meta Cloud API

O script `scripts/enviar_campanha_whatsapp.py` substitui a integração via Redrive por uma
conexão direta com a Meta Cloud API (`requests`) e usa a API da Anthropic (`anthropic`) para
gerar o texto das variáveis do template a partir de uma lista de clientes em CSV ou Excel.

### Instalação

```bash
cd scripts
pip install -r requirements.txt
cp .env.example .env  # preencha META_ACCESS_TOKEN, META_PHONE_NUMBER_ID e ANTHROPIC_API_KEY
```

### Uso

```bash
python enviar_campanha_whatsapp.py \
    --arquivo clientes_exemplo.csv \
    --template boas_vindas \
    --variavel "coluna:nome" \
    --variavel "ia:Escreva uma saudação curta e calorosa para {nome}, cliente da {loja}, sobre a promoção do mês." \
    --dry-run
```

- `--arquivo`: planilha `.csv` ou `.xlsx` com os clientes (uma coluna de telefone é obrigatória).
- `--variavel`: uma por variável do template, na ordem em que aparecem, em dois formatos:
  - `coluna:NOME_DA_COLUNA` — usa o valor da planilha direto.
  - `ia:PROMPT com {colunas}` — gera o texto com a Anthropic; o prompt pode referenciar
    qualquer coluna da planilha entre chaves.
- `--dry-run`: gera os textos e monta os payloads sem enviar, útil para conferir antes do envio real.
- Resultado de cada envio é salvo em `resultado_envio.csv` (configurável via `--saida`).

Rode `python enviar_campanha_whatsapp.py --help` para ver todas as opções (DDI padrão,
versão da Graph API, intervalo entre envios, limite de linhas para teste, etc.).