# Evidence Collectors

Os `Evidence Collectors` observam fontes explicitamente configuradas e produzem registros
versionados de evidência para o Coins on the Ground.

Eles não descobrem fontes sozinhos.

## Pipeline

```text
configuração local
      |
      v
fonte permitida
      |
      v
Evidence Collector
      |
      v
provider descriptor
      |
      v
CollectedEvidenceRecord
      |
      +-- source_id
      +-- source_ref
      +-- collected_at
      +-- payload_sha256
      +-- payload_bytes
      +-- normalized descriptor
```

O registro preserva provenance e um SHA-256 do payload bruto observado.

## Configuração

Formato:

```text
cog-evidence-sources-v1
```

Schema:

```text
schemas/evidence-sources-v1.schema.json
```

Exemplo:

```json
{
  "format": "cog-evidence-sources-v1",
  "sources": [
    {
      "id": "provider-a",
      "kind": "HTTPS_JSON",
      "location": "https://example.com/cog-evidence.json",
      "enabled": true,
      "max_bytes": 100000,
      "timeout_seconds": 10
    }
  ]
}
```

A URL acima é apenas exemplo.

## Tipos de fonte

### HTTPS_JSON

A fonte precisa ser uma URL HTTPS absoluta e entregar um descriptor JSON compatível.

Restrições da v1:

- HTTP sem TLS é rejeitado;
- usuário/senha embutidos na URL são rejeitados;
- redirects são rejeitados;
- a origem da resposta deve permanecer a origem configurada;
- o payload possui limite explícito de bytes;
- o `Content-Type` precisa indicar JSON;
- não há headers secretos ou autenticação automática nesta versão.

### LOCAL_JSON

Lê um descriptor JSON local relativo ao diretório do arquivo de configuração.

O caminho:

- precisa ser relativo;
- não pode escapar da raiz configurada por `..`;
- respeita o mesmo limite de bytes;
- entra na provenance como URI `file://`.

Esse modo é útil para snapshots deliberadamente importados ou fixtures auditáveis.

## Descriptor do provider

A fonte precisa produzir:

```text
cog-provider-evidence-v1
```

Schema:

```text
schemas/provider-evidence-v1.schema.json
```

O descriptor pode declarar:

```text
provider_name
capabilities
pricing
available
claims
max_age_days
expires_at
confidence_score
authorization_requirements
```

O collector define `observed_at` usando o instante real da coleta.

Isso evita aceitar como fato um timestamp arbitrário fornecido pela fonte para fingir frescor.

## Hash e provenance

Cada coleta registra:

```text
payload_sha256
payload_bytes
source_ref
collected_at
```

Duas observações do mesmo conteúdo terão o mesmo hash do payload, embora possam ter
`collected_at` diferentes.

O hash não prova que a fonte é verdadeira. Ele prova qual conteúdo bruto foi observado naquela
coleta.

## Falhas parciais

A coleta de múltiplas fontes produz um relatório com:

```text
records[]
failures[]
```

Se uma fonte falhar, os registros válidos das demais fontes não são descartados.

A falha preserva:

```text
source_id
source_kind
source_ref
error_type
message
```

Na CLI, a presença de falhas gera código de saída diferente de zero, mesmo que existam sucessos.
Isso permite que automação detecte coleta degradada sem perder as evidências obtidas.

## CLI

```bash
cog evidence-collect \
  --config ./examples/evidence-sources.example.json
```

Persistindo em JSONL:

```bash
cog evidence-collect \
  --config ./examples/evidence-sources.example.json \
  --output ./data/evidence-records.jsonl
```

Para fontes `LOCAL_JSON`, os caminhos são resolvidos em relação ao diretório que contém
`--config`.

## O que a v1 não faz

Os collectors não:

- fazem crawling;
- fazem busca aberta na web;
- extraem preço de HTML arbitrário;
- seguem redirects;
- usam cookies;
- usam credenciais;
- fazem login;
- resolvem CAPTCHA;
- modificam a fonte observada;
- atualizam automaticamente o catálogo de aquisição;
- tratam outro repositório como estado próprio;
- transformam uma observação em autorização de execução.

A separação é intencional:

```text
COLLECT
  -> RECORD
  -> ASSESS
  -> MATERIALIZE (futuro, explícito)
  -> PLAN
```

A etapa de materialização entre evidência coletada e catálogo continuará sendo explícita e
auditável.
