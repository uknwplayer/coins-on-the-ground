# Materialização de evidência

A materialização converte registros coletados em um novo catálogo de aquisição v2.

Ela é uma etapa explícita entre observação e planejamento:

```text
configured source
      |
      v
Evidence Collector
      |
      v
CollectedEvidenceRecord
      |
      v
Materialization Policy
      |
      v
Acquisition Catalog V2
      |
      v
Capability Acquisition Planner
```

## Separação de responsabilidades

A fonte externa pode declarar fatos observáveis como:

- capabilities oferecidas;
- preço;
- disponibilidade;
- requisitos de autorização;
- confiança e validade da informação.

Ela **não decide**:

- se deve ser tratada como `CONNECT_PROVIDER`;
- se deve estender um worker;
- se representa um adapter;
- qual `option_id` interno deve ser usado;
- qual perfil do Coins on the Ground deve ser alvo.

Essas decisões pertencem à policy local de materialização.

Isso preserva:

> Core knows capabilities. Project knows intentions.

e também a separação entre projetos.

## Policy

Formato:

```text
cog-evidence-materialization-v1
```

Schema:

```text
schemas/evidence-materialization-v1.schema.json
```

Exemplo:

```json
{
  "format": "cog-evidence-materialization-v1",
  "rules": [
    {
      "source_id": "provider-a",
      "option_id": "connect-provider-a",
      "mode": "CONNECT_PROVIDER",
      "target_profile": null,
      "reusable": true,
      "enabled": true,
      "setup_minutes_low": 2,
      "setup_minutes_high": 10
    }
  ]
}
```

Uma fonte habilitada só é materializada quando existe uma regra explícita para seu `source_id`.

## Record mais recente

Se o arquivo de records possuir múltiplas observações da mesma fonte, a materialização usa a
observação com `collected_at` mais recente.

O histórico não é apagado; apenas o catálogo novo usa a evidência mais recente disponível naquele
conjunto de records.

## Provenance no catálogo

O catálogo v2 materializado preserva:

```text
collector_source_id
payload_sha256
source_url
observed_at
```

Assim é possível rastrear:

```text
catalog option
     |
     v
payload_sha256
     |
     v
CollectedEvidenceRecord
     |
     v
source_ref
```

O `payload_sha256` precisa ser um digest SHA-256 válido. Um hash estruturalmente inválido torna a
evidência `INVALID`.

## Disponibilidade

Quando o descriptor declara:

```json
{
  "available": false
}
```

a opção ainda pode ser materializada para auditoria, mas entra no catálogo com:

```text
enabled = false
```

O sistema não apaga a observação histórica apenas porque a opção ficou indisponível.

## Fontes ausentes

Se uma rule referencia um `source_id` que não aparece nos records:

```text
missing_source_ids
```

é preenchido e o comando termina com código diferente de zero.

As opções das fontes presentes ainda podem ser gravadas no catálogo de saída.

Nenhuma option é inventada para a fonte ausente.

## Fontes não utilizadas

Records sem rule correspondente aparecem em:

```text
unused_source_ids
```

Isso não é erro por si só. Pode significar que uma fonte foi coletada para auditoria, mas ainda
não foi aprovada para participar do modelo econômico.

## CLI

Primeiro, coletar:

```bash
cog evidence-collect \
  --config ./examples/evidence-sources.example.json \
  --output ./data/evidence-records.jsonl
```

Depois, materializar:

```bash
cog evidence-materialize \
  --records ./data/evidence-records.jsonl \
  --policy ./examples/evidence-materialization.example.json \
  --output ./data/acquisition-catalog-v2.json
```

O catálogo gerado é validado novamente pelo parser do
`cog-capability-acquisition-catalog-v2` antes de ser gravado.

Depois pode ser inspecionado:

```bash
cog catalog-check \
  --catalog ./data/acquisition-catalog-v2.json
```

e usado pelo planner:

```bash
cog acquisition-plan frantic \
  --catalog ./data/acquisition-catalog-v2.json \
  --capability file_io
```

## Nenhuma atualização silenciosa

`evidence-collect` não modifica catálogo.

`evidence-materialize` cria um arquivo de saída explicitamente indicado.

`acquisition-plan` não modifica nem records nem catálogo.

A direção é sempre:

```text
immutable observation
      -> explicit transformation
      -> explicit planning
```

Isso mantém a trilha de auditoria legível e reversível.
