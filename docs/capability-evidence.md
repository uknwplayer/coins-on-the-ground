# Evidência para aquisição de capabilities

O catálogo de aquisição v2 adiciona evidência explícita às opções usadas pelo
`Capability Acquisition Planner`.

Formato:

```text
cog-capability-acquisition-catalog-v2
```

Schema:

```text
schemas/capability-acquisition-catalog-v2.schema.json
```

## Objetivo

Uma capability ou preço não deve ser tratado como fato apenas porque alguém escreveu um valor no
catálogo.

O v2 exige que cada opção declare a evidência que sustenta afirmações como:

- o provider oferece a capability;
- o preço observado é este;
- a opção estava disponível;
- existem requisitos de autorização ou elegibilidade.

## Evidence claims

A evidência pode sustentar uma ou mais claims:

### CAPABILITY

A fonte sustenta que a opção realmente oferece a capability declarada.

Sem essa claim válida, uma opção v2 não fecha um capability gap.

### PRICING

A fonte sustenta os valores econômicos informados no catálogo.

Sem essa claim válida, custos como `setup_cost_usd`, `per_task_cost_usd` e
`hourly_cost_usd` não são usados como preço confiável.

O resultado econômico permanece `UNKNOWN`.

### AVAILABILITY

A fonte sustenta que a opção estava disponível no momento da observação.

A ausência dessa claim não inventa indisponibilidade, mas fica registrada na rationale.

### AUTHORIZATION

A fonte contém informação relacionada a autorização, elegibilidade, conta, termos ou permissão.

Requisitos concretos continuam sendo declarados separadamente em
`authorization_requirements`.

## Freshness

Cada evidência possui:

```text
observed_at
expires_at
max_age_days
```

O sistema classifica a evidência como:

```text
FRESH
STALE
EXPIRED
INVALID
UNVERIFIED
```

### FRESH

A observação ainda está dentro de `max_age_days` e não expirou.

Somente evidência `FRESH` pode sustentar capability ou preço no catálogo v2.

### STALE

A observação ficou mais antiga que o limite declarado.

Um preço stale deixa de sustentar cálculo de lucro.

Uma capability stale deixa de fechar o gap.

### EXPIRED

`expires_at` já passou.

O comportamento econômico é conservador: a opção não é tratada como válida.

### INVALID

Há inconsistência estrutural ou temporal, por exemplo:

- URL de fonte inválida;
- `observed_at` no futuro;
- `expires_at` anterior ou igual a `observed_at`;
- confiança fora do intervalo permitido;
- `max_age_days` inválido.

### UNVERIFIED

Usado quando não há evidência anexada.

Catálogos v1 continuam suportados por compatibilidade, mas não recebem automaticamente as
garantias do modelo evidence-backed.

## Confidence

O catálogo possui um `confidence_score` da opção e a evidência possui outro.

No v2, a confiança efetiva do candidato é conservadora:

```text
effective_confidence =
    min(option_confidence, evidence_confidence)
```

Uma evidência fraca não é mascarada por um score alto colocado na opção.

## Requisitos de autorização

`authorization_requirements` registra requisitos explícitos conhecidos, por exemplo:

```text
- Provider account required
- Accepted terms required
- Organization membership required
```

A presença desses requisitos faz o planner marcar:

```text
requires_authorization_review = true
```

Isso não significa que a autorização esteja satisfeita.

## Exemplo

```json
{
  "format": "cog-capability-acquisition-catalog-v2",
  "options": [
    {
      "id": "example-transcription-provider",
      "mode": "CONNECT_PROVIDER",
      "provides": ["transcription"],
      "setup_cost_usd": "0",
      "per_task_cost_usd": "0.05",
      "confidence_score": 80,
      "evidence": {
        "source_name": "Provider pricing page",
        "source_url": "https://example.invalid/pricing",
        "observed_at": "2026-09-18T00:00:00Z",
        "expires_at": "2026-10-18T00:00:00Z",
        "max_age_days": 30,
        "claims": [
          "CAPABILITY",
          "PRICING",
          "AVAILABILITY"
        ],
        "confidence_score": 75,
        "authorization_requirements": [
          "Provider account required"
        ]
      }
    }
  ]
}
```

O domínio acima é apenas ilustrativo.

## Inspeção do catálogo

A evidência pode ser verificada sem executar Scouts:

```bash
cog catalog-check \
  --catalog ./examples/acquisition-catalog-v2.example.json
```

A saída mostra por opção:

```text
option_id
mode
provides
enabled
evidence_required
evidence.status
evidence.claims
evidence.confidence_score
source_url
authorization_requirements
```

E termina com um resumo:

```text
options
fresh_evidence_options
execution_performed=false
```

## Fronteira entre projetos

O v2 não autoriza o Coins on the Ground a pesquisar repositórios externos como fonte de estado.

A evidência precisa entrar no projeto por um processo deliberado:

```text
fonte externa
    |
    | observação/import explícito
    v
catálogo local do Coins on the Ground
    |
    v
evidence assessment
    |
    v
planner
```

O catálogo é uma observação local e versionada. A fonte externa continua independente.
