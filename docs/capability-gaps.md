# Capability Gap Planner

O `Capability Gap Planner` explica por que uma oportunidade pode ou não ser executada pelo
inventário atual de workers/endpoints.

Ele não cria capacidades, não instala ferramentas e não executa tarefas.

## Tipos de gap

### NONE

Pelo menos um perfil individual possui todas as capacidades exigidas.

### CAPABILITY_MISSING

Uma ou mais capacidades necessárias não aparecem em nenhum perfil direto do inventário.

Exemplo:

```text
tarefa exige: transcription + file_io

worker-a: file_io

resultado:
  CAPABILITY_MISSING
  missing: transcription
```

### COLOCATION

Todas as capacidades existem no inventário, mas estão espalhadas em perfis diferentes.

Exemplo:

```text
tarefa exige: transcription + file_io

worker-a: transcription
worker-b: file_io

resultado:
  COLOCATION
```

Esse caso é diferente de capacidade ausente. A infraestrutura possui as peças, mas nenhum
executor individual satisfaz o contrato completo.

### NO_INVENTORY

Nenhum inventário de capacidades foi fornecido.

### UNKNOWN_REQUIREMENTS

O estimator ainda não reconhece os requisitos técnicos da tarefa. O planner não inventa
capacidades ausentes.

## Regra de não união

O planner pode calcular a união global de capabilities apenas para **diagnóstico de gap**.

Essa união nunca é usada para declarar a tarefa `FEASIBLE`.

Feasibility continua sendo calculada perfil por perfil.

## Uso

Com registros da Machine Bridge:

```bash
cog gaps frantic \
  --machine-bridge-registration ./worker-a.json \
  --machine-bridge-registration ./worker-b.json \
  --limit 25
```

Com Mesh:

```bash
cog gaps all \
  --mesh-advertisement ./endpoint-a.json \
  --mesh-advertisement ./relay-a.json \
  --limit 100
```

Também é possível combinar registros importados e um perfil manual.

## Saída

O plano inclui:

```text
gap_type
required_capabilities
globally_available_capabilities
globally_missing_capabilities
feasible_profiles
nearest_profile
nearest_profile_missing
recommended_capabilities
rationale
```

`recommended_capabilities` não significa "instale automaticamente".

É uma descrição técnica do menor gap identificado para que uma decisão posterior possa avaliar:

- criar um novo worker;
- ampliar um worker existente;
- conectar um serviço externo;
- desenvolver um adapter;
- ignorar a oportunidade;
- executar manualmente;
- aguardar uma capacidade aparecer na Mesh.

## Relação com Machine Bridge / Mesh

A decisão sobre qual capacidade falta pertence ao Coins on the Ground.

A Machine Bridge e a Bridge Mesh continuam responsáveis apenas por anunciar, rotear e executar
capabilities sob seus próprios contratos e políticas.

Nenhuma alteração no core é necessária.
