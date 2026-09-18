# Capability Acquisition Planner

O `Capability Acquisition Planner` transforma um gap técnico em opções econômicas explícitas.

Ele responde:

> Se a capability necessária não está disponível, quais opções já cadastradas no próprio
> Coins on the Ground poderiam fechar esse gap, quanto custariam e a oportunidade continuaria
> economicamente interessante?

O planner é **somente planejamento**. Ele não instala ferramentas, não conecta providers, não cria
workers e não executa tarefas.

## Catálogo local e explícito

O planner não descobre providers automaticamente.

Ele só considera opções presentes em um catálogo fornecido explicitamente:

```text
Opportunity
    |
    v
Capability Gap
    |
    v
Local Acquisition Catalog
    |
    v
Acquisition Candidates
    |
    v
Economic Recalculation
```

Isso mantém a separação entre projetos e evita que um repositório externo seja tratado como
inventário, marketplace ou dependência implícita.

O formato do catálogo é:

```text
cog-capability-acquisition-catalog-v1
```

Schema:

```text
schemas/capability-acquisition-catalog-v1.schema.json
```

## Modos

### EXTEND_PROFILE

Planeja adicionar uma capability a um perfil existente.

### CONNECT_PROVIDER

Representa uma integração explicitamente cadastrada com um provider ou serviço capaz de fornecer
a capability.

O provider não é descoberto pelo planner; a opção precisa existir no catálogo local.

### BUILD_ADAPTER

Representa desenvolver ou habilitar um adapter local que exponha a capability necessária.

### ADD_PROFILE

Representa adicionar um novo perfil/worker que já ofereça o conjunto declarado de capabilities.

### ROUTE_CAPABILITY

Representa uma rota explicitamente conhecida e cadastrada que, se habilitada, entrega a capability
necessária ao contexto avaliado.

O planner não transforma `reachableCapabilities` genéricas em uma rota econômica válida por
conta própria.

## Custos

Uma opção pode declarar:

```text
setup_cost_usd
per_task_cost_usd
hourly_cost_usd
setup_minutes_low
setup_minutes_high
```

Valores financeiros desconhecidos permanecem `null`.

O sistema não interpreta `null` como zero.

## Amortização

Uma capability reutilizável pode ter custo de setup.

Exemplo:

```text
adapter:
  setup_cost = US$ 10
  per_task_cost = US$ 0
```

Para uma única oportunidade:

```text
effective_acquisition_cost = US$ 10
```

Se houver expectativa explícita de 10 usos:

```text
effective_acquisition_cost = US$ 1 por uso
```

O custo original continua registrado; apenas a análise econômica usa a divisão informada.

Na CLI:

```bash
--amortization-uses 10
```

## Seleção

O planner prioriza candidatos que:

1. cobrem todas as capabilities reconhecidas;
2. apresentam economia mais favorável;
3. têm menor custo conservador quando comparável;
4. possuem maior confiança declarada no catálogo.

`best_option_id` é uma prioridade técnica/econômica dentro do catálogo fornecido.

Ele **não** é autorização para executar a aquisição.

## Fallback

Quando nenhuma opção cobre o gap:

```text
NO_OPTION
fallback = IGNORE_OR_MANUAL_REVIEW
```

Quando os requisitos da tarefa não são reconhecidos:

```text
UNKNOWN_REQUIREMENTS
fallback = HUMAN_REVIEW
```

Quando a capability já existe:

```text
READY
fallback = USE_EXISTING
```

## CLI

Exemplo:

```bash
cog acquisition-plan frantic \
  --catalog ./examples/acquisition-catalog.example.json \
  --capability file_io \
  --hourly-cost-usd 0.60 \
  --amortization-uses 10 \
  --limit 25
```

Com inventário importado explicitamente:

```bash
cog acquisition-plan all \
  --catalog ./acquisition-catalog.json \
  --machine-bridge-registration ./worker-a.json \
  --mesh-advertisement ./endpoint-a.json \
  --limit 100
```

Os arquivos passados nesses argumentos pertencem ao contexto da execução do Coins on the Ground.
O comando não sai procurando registros em outros repositórios.

## Limites atuais

A v1:

- trabalha apenas com opções declaradas;
- não pesquisa preços de providers;
- não cria credenciais;
- não instala software;
- não modifica Machine Bridge ou Bridge Mesh;
- não assume que duas capabilities em workers diferentes possam ser compostas;
- não transforma recomendação econômica em autorização;
- ainda não aprende custos reais a partir de execuções históricas.

Essas limitações são intencionais.
