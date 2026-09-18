# Coins on the Ground

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
cog scan akash --limit 25
cog scan bidpostloop --limit 25
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
`docs/evidence-ledger.md`, `docs/historical-confidence.md` e
`docs/global-discovery.md`.

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
- Akash, BidPostLoop, GitHub, Frantic, IssueHunt OSS, Algora, Immunefi, Keep3r, Sherlock e Taskmarket;
- Source Registry `clearnet/onion` sem crawling automático;
- isolamento de falhas por Scout em agregações globais;
- reward semantics explícita para diferenciar payout exato, maximum bounty, maximum_rate, gross_escrow e pool_credits;
- descoberta read-only de Keep3r jobs com créditos positivos on-chain;
- descoberta read-only de Akash open compute orders;
- microtarefas financiadas de centavos via BidPostLoop;
- regras de custo específicas para microtasks, permitindo filtrar tarefas de US$0,05–0,10 por tempo esperado;
- Settlement Pool Summary que respeita budget financiado compartilhado em vez de somar slots de templates como cofres independentes;
- Microtask Portfolio Planner com prioridade por net conservador/minuto e rota de menor número de ações até payout;
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

A próxima evolução principal volta a ser **aumentar a superfície de descoberta**: novos Scouts
globais para recompensas on-chain permissionless, competições, compute/storage/bandwidth rewards,
mercados públicos de tarefas e fontes onion legítimas previamente revisadas. O pipeline econômico
e de evidência continuará filtrando essas descobertas depois da coleta.
