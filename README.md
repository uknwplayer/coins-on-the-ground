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
4. estima recompensa, custo e valor líquido esperado;
5. classifica risco jurídico/político do projeto;
6. prioriza candidatos para revisão humana;
7. preserva trilha de auditoria.

A execução será uma capacidade separada, introduzida apenas quando o pipeline de descoberta e
validação estiver confiável.

## Primeiro Value Scout real

O primeiro adaptador de fonte pesquisa issues públicas do GitHub em busca de bounties com
recompensa monetária explícita.

```bash
python -m pip install -e ".[dev]"
cog scan github-bounties --limit 25
```

Ele é intencionalmente conservador:

- não envia submissões;
- não faz claim;
- não movimenta ativos;
- não usa credenciais além de um token opcional do GitHub para ampliar limites da API;
- candidatos começam como `CIVIL_REVIEW`, não como aprovação automática de execução;
- na primeira versão, apenas recompensas explícitas denominadas em moeda fiduciária são extraídas.

Veja `docs/scouts.md`.

## Módulos iniciais

```text
src/coins_on_the_ground/
  scouts/          # descoberta de oportunidades
  classifiers/     # FOUND / EARN / RECOVER e classificação de risco
  opportunity/     # modelo canônico e scoring de oportunidades
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

A fundação e os primeiros Scouts somente leitura estão implementados. O objetivo atual é melhorar
a qualidade do sinal, adicionar validação específica por fonte e incorporar novas superfícies
independentes de oportunidade antes de considerar qualquer capacidade de execução.
