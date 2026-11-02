# Análise do SPX Raptor

Análise do fundo multimercado SPX Raptor só com dados públicos: 16 anos de cotas do informe diário da CVM e séries do Banco Central. A pergunta é a de um consultor de investimentos: pra que cliente esse fundo serve, e quanto da carteira alocar nele?

Resposta curta: posição satélite de 5 a 10% da carteira, pra investidor qualificado de horizonte longo, com acompanhamento de perto da gestora.

## Principais resultados

Período de dez/2010 a set/2026, em base mensal, antes do imposto de renda.

**Poder de compra de R$ 100 aplicados em dez/2010** (descontado o IPCA):

| Ativo | Valor hoje | Ganho real |
| --- | ---: | ---: |
| SPX Raptor | R$ 407 | +307% |
| SPX Nimitz | R$ 244 | +144% |
| IMA-B (fundo) | R$ 204 | +104% |
| CDI | R$ 184 | +84% |
| Ibovespa (fundo) | R$ 122 | +22% |

- **Risco:** maior queda de 27% a partir do topo (set/2022 a nov/2023), com 40 meses até recuperar. O Nimitz, no mesmo período, caiu 10%.
- **Proteção:** nos 10 piores meses do Ibovespa, o Raptor subiu em 7, ficou no zero em 1 e caiu em 2, nunca mais que 2,5%. Correlação com a bolsa: −0,15.
- **Raptor = 2 Nimitz:** no retorno acima do CDI, cada ponto do Nimitz vira 2 no Raptor. Como os dois cobram a mesma taxa, metade no Raptor e metade no CDI rende cerca de 1 ponto a mais por ano que tudo no Nimitz, com o mesmo risco.
- **Desde 2023:** Raptor +20%, Nimitz +34%, CDI +58%, IPCA +19%.
- **Conferência:** o acumulado do Raptor desde o início (885,90%) e o do Nimitz (491,63%) são iguais aos publicados pela gestora, assim como o melhor e o pior mês.

## Como funciona

Pipeline modular, um estágio por arquivo:

| Arquivo | Responsabilidade |
| --- | --- |
| `_extract.py` | Baixa o informe diário da CVM (arquivos anuais até 2020, mensais depois) e as séries do Banco Central, com cache local |
| `_schemas.py` | Contrato dos dados: barra cota zerada ou negativa, data duplicada e variação implausível antes de qualquer cálculo |
| `_transform.py` | Lê os arquivos da CVM em blocos de 500 mil linhas, filtra os fundos, unifica os dois formatos da CVM (antes e depois da Resolução 175) e trata retificações |
| `_load.py` | Grava as tabelas limpas em Parquet |
| `pipeline.py` | Orquestra os estágios em sequência |
| `metrics.py` | Retorno real, risco, drawdown, correlações, Raptor × Nimitz, piores meses da bolsa e dimensionamento por perfil |
| `settings.py` | Fundos analisados, séries e caminhos |

## Como rodar

Requer Python 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py   # na primeira vez baixa cerca de 1,4 GB da CVM
python metrics.py    # imprime as tabelas de resultado
```

## Dados

| Série | Fonte | Identificador |
| --- | --- | --- |
| SPX Raptor | CVM, informe diário | CNPJ 12.809.201/0001-13 |
| SPX Nimitz | CVM, informe diário | CNPJ 12.831.360/0001-14 |
| Ibovespa: Itaú Índex Ações Ibovespa | CVM, informe diário | CNPJ 03.370.003/0001-05 |
| IMA-B: Caixa Brasil IMA-B Títulos Públicos | CVM, informe diário | CNPJ 10.740.658/0001-93 |
| CDI diário | Banco Central, SGS | série 12 |
| IPCA | Banco Central, SGS | série 433 |
| Meta Selic | Banco Central, SGS | série 432 |
| Dólar (PTAX) | Banco Central, SGS | série 1 |

Ibovespa e IMA-B entram como fundos, e não como índices: são produtos que um cliente consegue comprar, com a taxa já descontada, como o Raptor.

## Limitações

- **Tudo é mensal.** Até 2024, a cota do Raptor só aparece nos dados da CVM no fim de cada mês. Por isso a volatilidade daqui (12,0% ao ano) difere da publicada pela gestora (11,45%), que usa uma série diária não pública. No Nimitz, que tem cota diária, os dois cálculos batem (5,19% contra 5,18%).
- **Antes do imposto.** As cotas já descontam as taxas, mas não o imposto de renda.
- **Não é recomendação de investimento.** É um estudo com dados públicos.

## Sobre

Feito como desafio técnico de um processo seletivo de estágio em consultoria de investimentos. Desenvolvido com Claude Code: a IA escreveu o código, e as decisões de método e a revisão de cada etapa foram minhas.

Licença: [GPLv3](LICENSE).
