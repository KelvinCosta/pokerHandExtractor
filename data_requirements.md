# 📊 Data Requirements & API Mapping

Para que o nosso Frontend deixe de ser apenas um "Mock" bonito e passe a exibir 100% da realidade do seu Datalake, nós precisaremos plugar as views do React aos endpoints que consumirão os nossos Parquets via Polars.

Abaixo está o levantamento de todas as rotas de API que precisaremos criar no **Milestone 4.5 (Integração de Dados)**.

---

## 1. Overview View (`/api/dashboard/overview`)
A visão geral de saúde do jogador.
- **`GET /kpis`**
  - **Dados:** `total_hands`, `profit_usd`, `profit_bb`, `bb_100`, `std_dev_bb100`, `total_sessions`.
  - **Status:** ⚠️ Parcialmente implementado (`/health`), mas precisa de revisão nos cálculos de torneio/ticket.
- **`GET /profit-trend`**
  - **Dados:** Array de `{ timestamp, cumulative_profit, all_in_ev }`.
  - **Uso:** Gráfico principal de linha (EV vs Realidade).
- **`GET /edge-distribution`**
  - **Dados:** Array de `{ category, bb_100, volume }` agrupado por Stake (NL2, NL5) ou Tipo (Rush, Spin).
  - **Uso:** Gráficos de barra menores (Onde o Hero ganha mais dinheiro?).

---

## 2. Analytics Bento (`/api/dashboard/analytics`)
O raio-x profundo do jogo do Hero.
- **`GET /leaks`**
  - **Dados:** `{ wwsf, wtsd, w_at_sd, red_line_profit, blue_line_profit }`.
  - **Uso:** Identificação de vazamentos de dinheiro (ex: foldando muito no river, ou blefando pouco).
- **`GET /time-analysis`**
  - **Dados:** Agrupamento de Winrate por Dia da Semana e Hora do Dia.
  - **Uso:** Heatmap de "Qual horário o field é mais fraco / Hero joga melhor".

---

## 3. Engines (Pre/Post-Flop) (`/api/dashboard/engines`)
Focado puramente nas estatísticas técnicas.
- **`GET /preflop`**
  - **Dados:** `{ vpip, pfr, three_bet, four_bet, squeeze, fold_to_3bet }` agrupados por Posição (BTN, CO, SB, BB, EP).
- **`GET /postflop`**
  - **Dados:** `{ cbet_flop, cbet_turn, cbet_river, fold_to_cbet, check_raise }`.
  - **Uso:** Identificar agressividade pós-flop.

---

## 4. Villain Mapping (`/api/dashboard/villains`)
O painel de rivalidade. Como o Polars extrai todos os nicks da mesa, podemos fazer o tracking!
- **`GET /rivals`**
  - **Dados:** Lista de `{ villain_name, hands_played, net_profit_against, bb_won_against, notes }`.
  - **Uso:** Tabela de maiores "doadores" (fishes) e maiores "carrascos" (regs).
- **`GET /population-tendencies`** (Population View)
  - **Dados:** Média do VPIP/PFR de todos os oponentes por limite jogado.
  - **Uso:** Mass Data Analysis (MDA) para saber como o field médio se comporta.

---

## 5. Big Pots & Audit (`/api/dashboard/audit`)
Replay e estudo.
- **`GET /big-pots`**
  - **Dados:** Lista de `{ hand_id, date, pot_size_bb, hole_cards, board, result_usd }` onde o pote foi maior que 50bb.
  - **Uso:** Tabela para revisão da sessão.
- **`POST /chat/hand-audit`**
  - **Dados:** Envia o ID de uma mão, e a API retorna o histórico formatado para o LLM criticar a jogada.

---

### 🛠️ Plano de Ação para o Backend
O legal de usarmos **Polars** é que todas essas requisições são extremamente fáceis de fazer com a sintaxe funcional de DataFrame. Como nosso Datalake (Silver) já está achatado e padronizado, cada endpoint desse levará poucas linhas de manipulação (GroupBy, Agg, Filter) para retornar o JSON certinho pro Frontend.
