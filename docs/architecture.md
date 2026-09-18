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
                    | Review Engine         |
                    |   |                   |
                    |   v                   |
                    | Cost & Feasibility    |
                    |   |                   |
                    |   v                   |
                    | Policies + Audit      |
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
- estimativa de viabilidade;
- perfis de capacidades para avaliação econômica;
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
  -> DEDUPLICATE
  -> REVIEW SCORE
  -> COST & FEASIBILITY ESTIMATE
  -> POLICY GATE
  -> HUMAN REVIEW
  -> AUDIT RECORD
```

A execução fica deliberadamente fora do primeiro marco.

## Integração futura de capacidades

O estimator recebe um `CapabilityProfile` pertencente ao Coins on the Ground.

No futuro, adapters poderão converter capacidades genéricas expostas pela Machine Bridge ou
Bridge Mesh nesse perfil. Isso mantém a direção da dependência correta:

```text
Machine Bridge / Bridge Mesh -> adapter -> CapabilityProfile -> estimator
```

As Bridges não precisam conhecer bounties, lucro, FOUND/EARN/RECOVER ou regras financeiras.

## Isolamento de repositórios

A fronteira arquitetural também é uma fronteira de repositório.

Um repositório externo pode ser usado como referência para compreender um contrato público, mas
seu estado operacional, workflows, arquivos internos e regras de negócio não pertencem ao
Coins on the Ground.

O projeto só deve consumir dados externos quando eles forem fornecidos deliberadamente por uma
interface/adaptador configurado para esta finalidade.

Em particular:

```text
outro projeto/repositório
        |
        | contrato público / export explícito
        v
adapter mantido em Coins on the Ground
        |
        v
modelo interno do Coins on the Ground
```

Não existe dependência implícita de repositório para repositório.

## Fronteira futura de execução

Quando a execução for introduzida, ela deverá ficar isolada atrás de uma interface explícita e
desabilitada por padrão. Componentes de descoberta nunca devem exigir custódia de credenciais ou
ativos.

Um executor futuro deverá receber uma `Opportunity` já revisada, além de uma decisão específica
de autorização. Ele não deve inferir propriedade ou permissão apenas a partir de acessibilidade
técnica.
