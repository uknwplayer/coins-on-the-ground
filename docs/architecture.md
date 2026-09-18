# Arquitetura

## Fronteira

Coins on the Ground é uma aplicação, não um fork da Machine Bridge nem da Bridge Mesh.

```text
                    +-----------------------+
                    | Coins on the Ground   |
                    |                       |
Fontes públicas --> | Scouts                |
                    |   |                   |
                    |   v                   |
                    | Opportunity Model     |
                    |   |                   |
                    |   v                   |
                    | Classifiers/Policies  |
                    |   |                   |
                    |   v                   |
                    | Economics + Audit     |
                    +----+-------------+----+
                         |             |
                     adapters      adapters
                         |             |
                         v             v
                 Machine Bridge   Bridge Mesh
                     Core             Core
```

## Regra

**Core knows capabilities. Project knows intentions.**

A Machine Bridge pode expor operações genéricas como execução de ferramentas, troca de mensagens,
handoff de tarefas, validação ou invocação de agentes.

A Bridge Mesh pode expor operações genéricas como distribuição, redundância, coordenação,
consenso, roteamento ou auditoria.

Coins on the Ground é responsável por conceitos como:

- descoberta de oportunidades;
- FOUND / EARN / RECOVER;
- evidência de autorização;
- estimativa de recompensa e custo;
- metadados de risco jurídico;
- limites de rentabilidade;
- política de execução;
- trilha de auditoria financeira.

Nenhum desses conceitos deve ser empurrado para os cores genéricos.

## Pipeline somente leitura

```text
SOURCE
  -> SCOUT
  -> NORMALIZE
  -> AUTHORIZATION EVIDENCE
  -> CLASSIFY
  -> ECONOMIC ESTIMATE
  -> POLICY GATE
  -> HUMAN REVIEW
  -> AUDIT RECORD
```

A execução fica deliberadamente fora do primeiro marco.

## Fronteira futura de execução

Quando a execução for introduzida, ela deverá ficar isolada atrás de uma interface explícita e
desabilitada por padrão. Componentes de descoberta nunca devem exigir custódia de credenciais ou
ativos.

Um executor futuro deverá receber uma `Opportunity` já revisada, além de uma decisão específica
de autorização. Ele não deve inferir propriedade ou permissão apenas a partir de acessibilidade
técnica.
