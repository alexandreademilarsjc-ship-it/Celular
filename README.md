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

## Atendimento automático (SDR/BDR com IA) — `atendimento_ia/`

Serviço web (FastAPI) que assume a conversa depois que o cliente responde ao primeiro contato:
recebe as mensagens via webhook da Meta, usa a Anthropic para responder como um SDR, e avisa
por WhatsApp quando o lead pede para falar com um representante.

### Como funciona

1. Cliente responde à mensagem inicial (enviada pelo script de campanha) → a Meta chama o
   webhook (`POST /webhook`) deste serviço.
2. O serviço salva a mensagem, monta o histórico da conversa e pede pra Anthropic gerar a
   próxima resposta — em formato estruturado, incluindo se o lead quer falar com um humano.
3. A resposta é enviada de volta pelo WhatsApp automaticamente.
4. Se o lead pediu para falar com um representante, o número configurado em
   `TELEFONE_ALEXANDRE` recebe um aviso com o resumo da conversa.

### Deploy no Railway

```bash
cd atendimento_ia
cp .env.example .env  # preencha as variáveis (veja comentários no arquivo)
```

No Railway: crie um novo projeto a partir deste repositório (ou faça upload da pasta
`atendimento_ia/`), configure as variáveis de ambiente do `.env` no painel do projeto, e
o deploy usa o `Procfile` automaticamente. Depois do deploy, pegue a URL pública gerada
(algo como `https://seu-projeto.up.railway.app`).

### Configurar o webhook na Meta

No app em developers.facebook.com → **WhatsApp → Configuração → Webhooks**:

- **URL de callback**: `https://sua-url-do-railway.up.railway.app/webhook`
- **Token de verificação**: o mesmo valor de `WEBHOOK_VERIFY_TOKEN` no `.env`
- Inscreva-se no campo **messages**

### Antes de usar em produção

O prompt em `conversa.py` (`SYSTEM_PROMPT`) tem um `TODO` para os detalhes reais da oferta
(condições de entrada, valor da carta de crédito, prazos) — preencha antes de ativar de
verdade, para a IA não inventar informação.