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

1. descobre oportunidades públicas;
2. normaliza cada descoberta em um modelo comum;
3. registra a fonte e a base de autorização;
4. deduplica achados equivalentes;
5. calcula prioridade para revisão;
6. estima capacidades, esforço e custo quando houver dados suficientes;
7. identifica gaps de capability;
8. simula opções locais de aquisição de capability;
9. valida evidência de capability/preço quando disponível;
10. preserva incerteza quando capacidades, custos ou evidências não forem conhecidos;
11. mantém execução fora do pipeline.

## Uso atual

Descoberta:

```bash
cog scan frantic --limit 25
cog scan github-bounties --limit 25
```

Revisão e deduplicação:

```bash
cog review all --limit 100
```

Estimativa de custo e viabilidade:

```bash
cog estimate frantic \
  --capability transcription \
  --capability file_io \
  --hourly-cost-usd 0.60 \
  --limit 25
```

Gap de capabilities:

```bash
cog gaps frantic \
  --capability file_io \
  --limit 25
```

Planejamento de aquisição com evidência:

```bash
cog acquisition-plan frantic \
  --catalog ./examples/acquisition-catalog-v2.example.json \
  --capability file_io \
  --hourly-cost-usd 0.60
```

Inspeção do catálogo:

```bash
cog catalog-check \
  --catalog ./examples/acquisition-catalog-v2.example.json
```

Veja `docs/scouts.md`, `docs/opportunity-model.md`, `docs/feasibility.md`,
`docs/bridge-integration.md`, `docs/capability-gaps.md`,
`docs/capability-acquisition.md` e `docs/capability-evidence.md`.

## Módulos iniciais

```text
src/coins_on_the_ground/
  scouts/          # descoberta de oportunidades
  opportunity/     # modelo canônico, deduplicação e scoring
  estimation/      # custo, esforço e viabilidade por CapabilityProfile
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
- explorar ativos de terceiros apenas porque estão tecnicamente acessíveis.

## Estado atual

Já estão implementados:

- Scouts públicos somente leitura;
- Opportunity Model;
- deduplicação;
- `review_score`;
- distinção entre custo zero e custo desconhecido;
- Cost & Feasibility Estimator com faixas de tempo/custo;
- `CapabilityProfile` explícito;
- classificação de viabilidade e rentabilidade;
- adapters compatíveis com contratos explícitos da Machine Bridge / Bridge Mesh;
- inventário por worker/endpoint, sem união artificial de capacidades;
- Capability Gap Planner;
- Capability Acquisition Planner;
- catálogo v1 declarado;
- catálogo v2 evidence-backed;
- `FRESH / STALE / EXPIRED / INVALID / UNVERIFIED`;
- claims `CAPABILITY / PRICING / AVAILABILITY / AUTHORIZATION`;
- inspeção de catálogo via `cog catalog-check`;
- amortização explícita de custos de setup;
- recálculo de custo e valor líquido após aquisição hipotética;
- testes automatizados e CI.

A próxima evolução é automatizar a **coleta deliberada de evidência para fontes configuradas**,
sem transformar a internet ou repositórios externos em estado implícito do projeto.
