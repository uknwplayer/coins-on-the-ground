# Convenções do projeto

## Idioma

### Conteúdo destinado a humanos

Documentação, explicações arquiteturais, guias operacionais, notas de decisão e demais textos
destinados principalmente à leitura humana devem ser escritos em **português (pt-BR)**.

### Elementos técnicos

Podem ser escritos em **inglês** quando isso for tecnicamente conveniente, idiomático ou melhorar
interoperabilidade:

- código-fonte;
- nomes de classes e funções;
- identificadores;
- schemas;
- campos JSON;
- nomes de eventos;
- nomes de protocolos;
- nomes de comandos;
- interfaces;
- tipos;
- enums;
- nomes de arquivos quando fizer sentido técnico;
- contratos entre componentes.

Não é necessário traduzir termos técnicos estabelecidos apenas para manter aparência de
uniformidade linguística.

## Escopo

Esta convenção pertence exclusivamente ao projeto **Coins on the Ground**.

Ela não altera os padrões, documentação ou código-base da **Machine Bridge** nem da
**Bridge Mesh**.

## Isolamento entre repositórios

Repositórios de projetos diferentes devem permanecer separados.

Coins on the Ground não deve:

- importar regras de negócio de outro projeto;
- usar estado operacional de outro projeto como se fosse estado próprio;
- escrever arquivos em outro repositório para implementar comportamento de Coins on the Ground;
- assumir que um repositório externo pertence a este projeto apenas porque contém código
  compatível, histórico relacionado ou uma implementação de referência;
- criar dependência implícita de caminhos, branches, workflows ou dados internos de outro projeto.

Integrações entre projetos devem acontecer apenas por interfaces explícitas, contratos públicos,
artefatos deliberadamente exportados ou adapters mantidos no repositório consumidor.

Se Machine Bridge ou Bridge Mesh forem consumidas pelo Coins on the Ground, o adapter específico
fica neste projeto. Os repositórios de origem continuam independentes.

Inspeção de um repositório externo para compreender um contrato não o transforma em dependência de
runtime, fonte de estado ou parte do projeto.
