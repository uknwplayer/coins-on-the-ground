# Integração com Machine Bridge e Bridge Mesh

## Objetivo

Coins on the Ground pode consumir anúncios de capacidades da Machine Bridge e da Bridge Mesh sem
alterar o core de nenhuma das duas arquiteturas.

A integração existe somente neste repositório:

```text
Machine Bridge Worker Registration V1
                 |
                 v
      Machine Bridge Adapter
                 |
                 +----------+
                            |
Bridge Mesh Node Advertisement V1
                 |          |
                 v          v
          Mesh Adapter -> CapabilityObservation
                            |
                            v
                     CapabilityProfile
                            |
                            v
                Cost & Feasibility Estimator
```

## Contratos consumidos

### Machine Bridge

O adapter entende o contrato já existente:

```text
format: arca-worker-registration-v1
protocolVersion: 3
worker.format: arca-worker-v1
worker.workerId
worker.capabilities[]
worker.heartbeatAt
```

O adapter lê apenas os campos necessários para observar capacidades. Ele não modifica o registro
nem o protocolo.

### Bridge Mesh

O adapter entende anúncios:

```text
format: arca-mesh-node-v1
meshVersion: 1
nodeId
kind: relay | endpoint | hybrid
capabilities[]
reachableCapabilities[]
heartbeatAt
```

Anúncios assinados que encapsulem esse node em `payload` também podem ser lidos como observação.
A validação criptográfica da assinatura continua sendo responsabilidade da infraestrutura Mesh;
o adapter do Coins on the Ground não inventa confiança criptográfica.

## Regra crítica: capacidade direta != capacidade alcançável

`capabilities` descreve o que o nó anuncia diretamente.

`reachableCapabilities` descreve o que pode ser alcançado por roteamento.

Coins on the Ground **não promove** `reachableCapabilities` para capacidades locais do relay.

Exemplo:

```json
{
  "nodeId": "relay-a",
  "kind": "relay",
  "capabilities": ["mesh.relay"],
  "reachableCapabilities": ["browser", "transcription"]
}
```

Esse registro não vira uma máquina com browser + transcription.

Ele continua sendo um relay. A informação de alcance é preservada para futura lógica de
roteamento, mas não é usada para declarar `FEASIBLE` em um executor local.

## Sem união artificial de workers

Se:

```text
worker-a = transcription
worker-b = file_io
```

e uma tarefa exige:

```text
transcription + file_io
```

o sistema não cria:

```text
worker-fictício = transcription + file_io
```

Cada worker/endpoint recebe sua própria estimativa. Só um perfil individual que satisfaça as
capacidades pode ser classificado como `FEASIBLE`.

## Mapeamento conservador

Machine Bridge aceita nomes de capacidade genéricos e extensíveis. Coins on the Ground possui um
vocabulário econômico menor para seu estimator.

O adapter mapeia apenas aliases explícitos, por exemplo:

```text
browser / browser.session        -> browser
media.transcription              -> transcription
document.ocr                     -> ocr
reasoning / llm.reasoning        -> text_analysis
git / repository.git             -> git
file_io / filesystem             -> file_io
```

Capacidades específicas que não garantem semanticamente uma capacidade genérica permanecem
`unmapped`.

Por exemplo:

```text
aie
node
pncp-plan
repository
mesh.relay
```

não são transformadas automaticamente em browser, code, git, text_analysis ou HTTP.

Isso evita que o estimator confunda uma capacidade especializada com uma permissão operacional
mais ampla.

## CLI

Inspecionar um registro da Machine Bridge:

```bash
cog capabilities \
  --machine-bridge-registration ./github-actions.json
```

Inspecionar um anúncio Mesh:

```bash
cog capabilities \
  --mesh-advertisement ./mesh-node.json
```

Combinar múltiplos registros:

```bash
cog capabilities \
  --machine-bridge-registration ./worker-a.json \
  --machine-bridge-registration ./worker-b.json \
  --mesh-advertisement ./endpoint-a.json
```

Estimar oportunidades contra esse inventário:

```bash
cog estimate all \
  --machine-bridge-registration ./worker-a.json \
  --mesh-advertisement ./endpoint-a.json \
  --hourly-cost-usd 0.60 \
  --limit 100
```

`--hourly-cost-usd` é uma hipótese econômica fornecida pelo Coins on the Ground para aquela
execução. Esse custo não é atribuído à Machine Bridge nem gravado no core.

## Estado atual da integração

O adapter já é compatível com os formatos de registro usados pelo ARCA Core observado durante o
desenvolvimento deste projeto.

O worker atual observado anuncia capacidades específicas como `aie`, `node`, `pncp-plan` e
`repository`. O mapeamento conservador não trata nenhuma delas como browser, OCR ou transcription.

Isso é um resultado útil: a infraestrutura consegue dizer não apenas quais oportunidades existem,
mas também quais lacunas de capacidade impedem sua execução hoje.

## Próxima evolução

O próximo passo natural é adicionar um **Capability Gap Planner**:

```text
Opportunity
   |
   v
required capabilities
   |
   +--> available now
   |
   +--> missing
          |
          v
    capability gap
          |
          v
"qual worker/adaptador seria necessário?"
```

Essa lógica continuará pertencendo ao Coins on the Ground. As Bridges continuarão apenas
anunciando e roteando capacidades genéricas.
