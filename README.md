# Coins on the Ground

[![Powered by RustChain](https://img.shields.io/badge/Powered%20by-RustChain-orange)](https://rustchain.org)

Coins on the Ground é um sistema experimental para descobrir pequenas oportunidades econômicas
legítimas que humanos tendem a ignorar por serem fragmentadas, de baixo valor, técnicas ou caras
de localizar manualmente.

O projeto foi desenhado como uma camada de aplicação capaz de usar **Machine Bridge** e
**Bridge Mesh** sem modificar o núcleo de nenhuma das duas arquiteturas.

## Regra de linguagem

Documentação destinada a humanos deve ser escrita em **português (pt-BR)**.

Código, identificadores, schemas, campos JSON, nomes de classes/funções, comandos, nomes de
protocolos e demais elementos técnicos podem permanecer em **inglês** quando isso for mais
conveniente ou idiomático.

Essa regra vale para todo o projeto Coins on the Ground e não altera os padrões dos projetos
Machine Bridge ou Bridge Mesh.

## Ideia central

Buscar valor econômico que possa ser legitimamente:

- **FOUND** — explicitamente reivindicável ou publicamente disponível segundo protocolo, contrato,
  promoção, bounty ou regra equivalente.
- **EARNED** — obtido após realizar trabalho útil, como computação, código, análise, armazenamento,
  validação, resolução de problemas ou outras tarefas remuneradas.
- **RECOVERED** — devolvido ao beneficiário legítimo quando o valor já pertence ao usuário ou a
  outro principal representado com autorização.

O sistema deve distinguir **"tecnicamente acessível"** de **"legitimamente adquirível"**.

## Regra arquitetural

> Core knows capabilities. Project knows intentions.

Machine Bridge e Bridge Mesh permanecem genéricas. Coins on the Ground contém todas as regras
específicas de descoberta, modelos econômicos, classificação de risco jurídico, scoring de
oportunidades e políticas de execução deste projeto.

```text
Machine Bridge Core <-> Adapter <-> Coins on the Ground <-> Adapter <-> Bridge Mesh Core
```

Comportamentos específicos de Coins on the Ground não devem ser implementados nos repositórios
core das Bridges.

## MVP: somente leitura primeiro

O primeiro marco **não** movimenta dinheiro nem ativos.

Ele:

1. descobre oportunidades públicas em fontes globais, sem filtro prévio por país;
2. normaliza cada descoberta em um modelo comum;
3. registra a fonte e a base de autorização;
4. deduplica achados equivalentes;
5. calcula prioridade para revisão;
6. estima capacidades, esforço e custo quando houver dados suficientes;
7. identifica gaps de capability;
8. simula opções locais de aquisição de capability;
9. coleta evidência apenas de fontes explicitamente configuradas;
10. preserva hash e provenance do payload observado;
11. materializa evidência em catálogo por policy explícita;
12. valida freshness, claims e requisitos de autorização;
13. registra observações em um Evidence Ledger local append-only;
14. detecta drift de preço, capability, disponibilidade, claims e autorização;
15. aplica uma Historical Confidence Policy explícita;
16. rebaixa ou bloqueia opções de aquisição com histórico insuficiente ou incompatível;
17. mantém execução fora do pipeline.

## Uso atual

Descoberta:

```bash
cog scan agent-bounties --limit 25
cog scan akash --limit 25
cog scan bidpostloop --limit 25
cog scan clawlancer --limit 25
cog scan frantic --limit 25
cog scan github-bounties --limit 25
cog scan issuehunt --limit 25
cog scan algora --limit 25
cog scan immunefi --limit 25
cog scan keep3r --limit 25
cog scan sherlock --limit 25
cog scan taskmarket --limit 25
```

Algora também aceita organizações explícitas:

```bash
cog scan algora \
  --org projectdiscovery \
  --org Dokploy \
  --limit 25
```

Registry global de fontes:

```bash
cog sources-check \
  --registry ./examples/scout-source-registry.example.json
```

Revisão:

```bash
cog review all --limit 100
```

Capacidade de atravessar payout mínimo em microtarefas:

```bash
cog settlement-summary bidpostloop --limit 100
```

Snapshots de replenishment:

```bash
cog replenishment-snapshot bidpostloop \
  --ledger ./data/opportunity-snapshots.jsonl \
  --limit 100

cog replenishment-analyze \
  --ledger ./data/opportunity-snapshots.jsonl \
  --source-id bidpostloop
```

Alocação de atenção entre fontes:

```bash
cog source-allocation all \
  --snapshot-ledger ./data/opportunity-snapshots.jsonl \
  --capability http \
  --capability text_analysis \
  --hourly-cost-usd 0.60 \
  --limit 100
```

Cadência adaptativa de scouting:

```bash
cog scout-cadence all \
  --snapshot-ledger ./data/opportunity-snapshots.jsonl \
  --capability http \
  --capability text_analysis \
  --hourly-cost-usd 0.60 \
  --scan-budget-per-day 24 \
  --min-scans-per-source-per-day 1 \
  --max-scans-per-source-per-day 6 \
  --limit 100
```

Ciclo persistente adaptativo:

```bash
cog scout-cycle \
  --snapshot-ledger ./data/opportunity-snapshots.jsonl \
  --state ./data/adaptive-scout-state.json \
  --scan-budget-per-day 24 \
  --min-scans-per-source-per-day 1 \
  --max-scans-per-source-per-day 6 \
  --refresh-interval-hours 24 \
  --retry-base-minutes 60 \
  --retry-max-minutes 1440 \
  --limit 100
```

Portfolio econômico de microtarefas:

```bash
cog portfolio bidpostloop \
  --capability http \
  --capability text_analysis \
  --hourly-cost-usd 0.60 \
  --current-balance-usd 0 \
  --limit 100
```

Estimativa de custo e viabilidade:

```bash
cog estimate frantic \
  --capability transcription \
  --capability file_io \
  --hourly-cost-usd 0.60
```

Gap de capabilities:

```bash
cog gaps frantic \
  --capability file_io
```

Coleta explícita de evidência:

```bash
cog evidence-collect \
  --config ./examples/evidence-sources.example.json \
  --output ./data/evidence-records.jsonl
```

Registro histórico:

```bash
cog evidence-ledger-append \
  --records ./data/evidence-records.jsonl \
  --ledger ./data/evidence-ledger.jsonl
```

Análise de drift:

```bash
cog evidence-ledger-analyze \
  --ledger ./data/evidence-ledger.jsonl
```

Confiança histórica:

```bash
cog historical-confidence \
  --ledger ./data/evidence-ledger.jsonl \
  --policy ./examples/historical-confidence-policy.example.json
```

Materialização explícita:

```bash
cog evidence-materialize \
  --records ./data/evidence-records.jsonl \
  --policy ./examples/evidence-materialization.example.json \
  --output ./data/acquisition-catalog-v2.json
```

Inspeção:

```bash
cog catalog-check \
  --catalog ./data/acquisition-catalog-v2.json
```

Planejamento:

```bash
cog acquisition-plan frantic \
  --catalog ./data/acquisition-catalog-v2.json \
  --ledger ./data/evidence-ledger.jsonl \
  --historical-policy ./examples/historical-confidence-policy.example.json \
  --capability file_io
```

Veja `docs/scouts.md`, `docs/opportunity-model.md`, `docs/feasibility.md`,
`docs/bridge-integration.md`, `docs/capability-gaps.md`,
`docs/capability-acquisition.md`, `docs/capability-evidence.md`,
`docs/evidence-collectors.md`, `docs/evidence-materialization.md` e
`docs/evidence-ledger.md`, `docs/historical-confidence.md`,
`docs/global-discovery.md`, `docs/replenishment.md`, `docs/source-allocation.md` e
`docs/scout-cadence.md`.

## Módulos iniciais

```text
src/coins_on_the_ground/
  scouts/          # descoberta de oportunidades
  opportunity/     # modelo canônico, deduplicação e scoring
  estimation/      # custo, esforço e viabilidade por CapabilityProfile
  evidence/        # coleta, provenance e materialização explícita
  classifiers/     # FOUND / EARN / RECOVER e classificação de risco
  planning/        # gaps, evidência e aquisição de capabilities
  policies/        # regras específicas deste projeto
  audit/           # evidências e trilha de decisão
  adapters/        # integração com Machine Bridge / Bridge Mesh
  execution/       # futuro; intencionalmente inativo no MVP
```

## Fora de escopo

O projeto não foi criado para:

- tratar ativos inativos ou mal protegidos como se não tivessem dono;
- usar credenciais vazadas ou chaves privadas de terceiros;
- contornar autenticação ou autorização;
- induzir sistemas ou pessoas a erro;
- explorar ativos de terceiros apenas porque estão tecnicamente acessíveis;
- fazer crawling aberto para preencher automaticamente o catálogo.

## Estado atual

Já estão implementados:

- Scouts públicos somente leitura;
- descoberta global sem filtro geográfico prévio;
- Agent Bounties, Akash, BidPostLoop, Clawlancer, GitHub, Frantic, IssueHunt OSS, Algora, Immunefi, Keep3r, Sherlock e Taskmarket;
- Source Registry `clearnet/onion` sem crawling automático;
- isolamento de falhas por Scout em agregações globais;
- reward semantics explícita para diferenciar payout exato, maximum bounty, maximum_rate, gross_escrow e pool_credits;
- descoberta read-only de Keep3r jobs com créditos positivos on-chain;
- descoberta read-only de Akash open compute orders;
- bounties canônicos claimable na Base via Agent Bounties, exigindo funding completo, termos válidos e verifier ready;
- microtarefas financiadas de centavos via BidPostLoop;
- bounties USDC ativos do Clawlancer com payout pós-fee do escrow V2;
- regras de custo específicas para microtasks, permitindo filtrar tarefas de US$0,05–0,10 por tempo esperado;
- Settlement Pool Summary que respeita budget financiado compartilhado em vez de somar slots de templates como cofres independentes;
- Microtask Portfolio Planner com prioridade por net conservador/minuto e rota de menor número de ações até payout;
- Opportunity Snapshot Ledger append-only para medir replenishment observado;
- métricas de funding positivo/negativo, entrada/saída de oportunidades e taxa normalizada por dia;
- Source Allocation Planner para distribuir atenção de scouting por qualidade atual, economia, replenishment, settlement e confiança histórica;
- `attention_share_pct` relativo, com unknown signals reduzindo cobertura em vez de virarem zero silenciosamente;
- Adaptive Scout Cadence com budget diário, piso de exploração e teto por fonte;
- recomendação `recommended_scans_per_day + target_interval_minutes`;
- `AdaptiveScoutState` persistente com `last_scanned_at`, `next_due_at` e refresh completo separado;
- `cog scout-cycle` com modos `full_refresh` e `due_only`, consultando apenas Scouts vencidos entre refreshes completos;
- workflow `.github/workflows/adaptive-scout.yml` agendado de hora em hora, com cache de ledger/state e artifact por ciclo;
- perda de cache provoca cold start seguro com nova varredura completa;
- health por Scout com `HEALTHY / BACKING_OFF / DEGRADED / UNKNOWN`;
- exponential retry backoff técnico de 60 min até 24h, separado da prioridade econômica;
- classificação técnica `RATE_LIMIT / TIMEOUT / SERVER_ERROR / CLIENT_ERROR / NETWORK_ERROR / OTHER`;
- suporte a `Retry-After` como piso de retry quando a fonte publica um hint maior;
- estado v3 backward-compatible com caches v1/v2;
- Opportunity Model e deduplicação;
- `review_score`;
- Cost & Feasibility Estimator;
- `CapabilityProfile` explícito;
- adapters para contratos explícitos das Bridges;
- Capability Gap Planner;
- Capability Acquisition Planner;
- catálogo v1 declarado;
- catálogo v2 evidence-backed;
- Evidence Collectors `HTTPS_JSON` e `LOCAL_JSON`;
- SHA-256 e provenance por observação;
- relatório de coleta com sucessos e falhas parciais;
- policy `cog-evidence-materialization-v1`;
- materialização explícita record → catálogo v2;
- provenance `collector_source_id + payload_sha256` no catálogo;
- Evidence Ledger local append-only;
- `entry_id` determinístico e deduplicação de observações;
- drift `PRICING / CAPABILITIES / AVAILABILITY / CLAIMS / AUTHORIZATION / CONTENT`;
- métricas observáveis de estabilidade e faixa de preço;
- Historical Confidence Policy `PASS / REVIEW / FAIL`;
- integração opcional ledger + policy no Capability Acquisition Planner;
- prioridade `PASS > REVIEW > sem avaliação > FAIL`;
- `FRESH / STALE / EXPIRED / INVALID / UNVERIFIED`;
- claims `CAPABILITY / PRICING / AVAILABILITY / AUTHORIZATION`;
- testes automatizados e CI.

A descoberta adaptativa já está operacionalmente ligada a um scheduler read-only no GitHub Actions.
O workflow roda em cadência horária, persiste ledger/state por cache e faz refresh global completo a
cada 24 horas por padrão. Entre refreshes, apenas Scouts cujo `next_due_at` venceu são consultados.
O próximo avanço passa a ser aumentar a superfície de descoberta e aprender políticas melhores de
retry/backoff e observabilidade sem aproximar o scheduler de execução financeira.
