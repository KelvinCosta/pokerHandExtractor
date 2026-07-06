# [Goal Description]

Corrigir a contabilização de lucros e prejuízos no Dashboard para separar Fichas de Torneio (Chips) de Dólares Reais (USD), integrando os Sumários de Torneio na conta financeira.

Atualmente, o Extrator salva o saldo das mãos (recebido - investido) na coluna `hero_net_profit`. Em Cash Games, isso representa Dólares. Em Torneios (Spin & Gold, MTTs), isso representa Fichas. Como o Dashboard soma o `hero_net_profit` assumindo que tudo é Dólar, o gráfico financeiro fica corrompido com milhões de "fichas de torneio".

## User Review Required

> [!IMPORTANT]
> **Integração de Torneios:** Para corrigir isso, os dados financeiros de Torneios virão exclusivamente do arquivo `tournaments.parquet` (Sumários: Prêmio - Buy-in), enquanto a performance tática (BB/100, VPIP, PFR) continuará vindo das mãos.
> 
> Como o banco `hands.parquet` antigo de vocês possui o erro estrutural (fichas misturadas com dólares na mesma coluna), após aplicarmos essa refatoração no ETL, você precisará apagar a camada `silver/` no MinIO e rodar o Extrator novamente. Tudo bem para você?

## Proposed Changes

### ETL Layer (Data Processing)

#### [MODIFY] [loader.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/src/etl/loader.py)
- Alterar a extração da mão para separar os ganhos. Criaremos as colunas:
  - `hero_net_profit_usd`: `(collected - invested)` se for Cash Game. Se for Torneio, recebe `0.0`.
  - `hero_net_chips`: `(collected - invested)` se for Torneio. Se for Cash Game, recebe `0.0`.
  - `hero_net_profit_bb`: Pre-calculada no ETL dividindo o `net_profit_usd` ou o `net_chips` pelo `stake_level` da mão (que em torneios é o Big Blind em fichas). Isso garante que o cálculo de BB/100 funcione perfeitamente para qualquer modalidade.

### API Layer (Dashboard & Dependencies)

#### [MODIFY] [dependencies.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/src/api/dependencies.py)
- Criar a função auxiliar `get_filtered_tournaments_df` para ler o `tournaments.parquet` aplicando os mesmos filtros globais de data.

#### [MODIFY] [dashboard.py](file:///c:/Desenvolvimento/DataScience/pokerHandExtractor/backend/src/api/routers/dashboard.py)
- **`/health`**: 
  - Somar o total de `hero_net_profit_usd` das mãos.
  - Ler o Datalake de torneios (`tournaments.parquet`), somar `(prize - buy_in)` e adicionar ao lucro total em USD.
  - O cálculo de `bb_100` usará a nova coluna `hero_net_profit_bb`.
- **`/profit-trend`**:
  - Combinar (join / concat ordenado por data) as mãos de Cash Game (`hero_net_profit_usd`) com os sumários de Torneio concluídos (`prize - buy_in`) para montar o gráfico de evolução do Bankroll real.
- **`/stake-breakdown`**:
  - Atualizar para agrupar usando `hero_net_profit_usd` e exibir o Winrate usando `hero_net_profit_bb`.

## Verification Plan

### Manual Verification
1. Limpar a camada `silver/` no MinIO local.
2. Rodar o extrator processando uma pasta que tenha arquivos de Cash Game e Torneios/Spin&Gold.
3. Chamar as rotas `/api/dashboard/health` e `/profit-trend`.
4. Verificar se o lucro USD reflete estritamente os resultados reais (Cash Games + Prêmios de Torneios subtraídos dos Buy-ins), e se o gráfico não dispara para os milhões devido a mãos de torneio.
