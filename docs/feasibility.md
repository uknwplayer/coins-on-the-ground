# Cost & Feasibility Estimator

O `Cost & Feasibility Estimator` estima se uma oportunidade parece compatível com um ambiente de
execução declarado e qual faixa de custo operacional ela pode ter.

Ele não executa tarefas, não faz claim e não movimenta valor.

## Princípio

O estimator não presume capacidades.

Sem um `CapabilityProfile` configurado, a viabilidade permanece `UNKNOWN`.

Isso é importante porque o projeto não deve confundir "o sistema conhece essa tarefa" com
"existe uma máquina disponível capaz de realizá-la".

## CapabilityProfile

Um perfil declara, por exemplo:

```text
browser
file_io
transcription
text_analysis
code
git
ocr
email
http
```

Também pode declarar um custo operacional por hora em USD.

No futuro, um adapter local do Coins on the Ground poderá montar esse perfil a partir das
capacidades expostas pela Machine Bridge ou Bridge Mesh. Nenhuma alteração nos cores dessas
arquiteturas é necessária.

## Estimativas em faixa

A primeira versão usa regras heurísticas auditáveis e produz:

- capacidades necessárias;
- capacidades ausentes;
- `FEASIBLE / PARTIAL / NOT_FEASIBLE / UNKNOWN`;
- faixa de minutos estimados;
- faixa de custo operacional;
- faixa de valor líquido esperado, quando comparável;
- `POSITIVE / UNCERTAIN / NEGATIVE / UNKNOWN` para rentabilidade;
- `confidence_score`;
- razões que explicam a estimativa.

A faixa evita falsa precisão. Uma tarefa estimada entre 5 e 20 minutos não deve ser apresentada
como se soubéssemos que durará exatamente 11 minutos.

## Exemplo

```bash
cog estimate frantic \
  --capability transcription \
  --capability file_io \
  --hourly-cost-usd 0.60 \
  --limit 25
```

Uma saída pode conter campos equivalentes a:

```json
{
  "feasibility": "FEASIBLE",
  "required_capabilities": ["file_io", "transcription"],
  "missing_capabilities": [],
  "estimated_minutes_low": 7,
  "estimated_minutes_high": 30,
  "estimated_cost_usd_low": "0.07",
  "estimated_cost_usd_high": "0.30",
  "profitability": "POSITIVE",
  "confidence_score": 90
}
```

Os valores acima são apenas exemplo de formato.

## Sem perfil configurado

Também é possível rodar:

```bash
cog estimate all --limit 100
```

Nesse caso o sistema ainda pode reconhecer o tipo de tarefa e estimar tempo, mas não afirma que
uma máquina consegue executá-la e não inventa custo operacional.

## Limitações da v1

A versão inicial usa regras textuais para tipos recorrentes de tarefa, incluindo OCR, transcrição,
análise de documentos, browser, email e desenvolvimento de software.

Ela ainda não:

- inspeciona profundamente o conteúdo completo da tarefa;
- mede tamanho de arquivos;
- calcula custo real de tokens/API;
- conhece limites reais de uma Machine Bridge;
- considera autenticação específica necessária;
- estima risco de rejeição da entrega;
- converte moedas;
- aprende automaticamente com execuções passadas.

Esses pontos são extensões planejadas.
