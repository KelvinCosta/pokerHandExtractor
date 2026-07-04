// Realistic mock telemetry for the poker BI dashboard.
// All monetary values in USD. Rates in bb/100 (big blinds per 100 hands).

export type Trend = "up" | "down" | "flat"

export interface Kpi {
  id: string
  label: string
  value: string
  raw: number
  delta: string
  trend: Trend
  hint: string
}

export const healthKpis: Kpi[] = [
  {
    id: "profit",
    label: "Net Profit",
    value: "$184,920",
    raw: 184920,
    delta: "+12.4%",
    trend: "up",
    hint: "Lifetime tracked winnings",
  },
  {
    id: "winrate",
    label: "Win Rate",
    value: "6.8 bb/100",
    raw: 6.8,
    delta: "+0.9",
    trend: "up",
    hint: "Big blinds per 100 hands",
  },
  {
    id: "hands",
    label: "Hands Played",
    value: "1.42M",
    raw: 1420000,
    delta: "+38.2k",
    trend: "up",
    hint: "Total tracked hands",
  },
  {
    id: "ev",
    label: "All-in Adj. (EV)",
    value: "+$9,410",
    raw: 9410,
    delta: "Run-good",
    trend: "up",
    hint: "Actual vs expected all-in",
  },
  {
    id: "std",
    label: "Std Deviation",
    value: "84 bb/100",
    raw: 84,
    delta: "-3.1",
    trend: "down",
    hint: "Variance of results",
  },
  {
    id: "sessions",
    label: "Sessions",
    value: "2,184",
    raw: 2184,
    delta: "+41",
    trend: "up",
    hint: "Distinct sessions logged",
  },
]

// Cumulative profit time-series (last 26 weeks). Green profit / EV overlay.
export interface ProfitPoint {
  week: string
  profit: number
  ev: number
}

export const profitSeries: ProfitPoint[] = (() => {
  const out: ProfitPoint[] = []
  let profit = 92000
  let ev = 92000
  for (let i = 0; i < 26; i++) {
    const swing = Math.round((Math.sin(i / 2.1) + Math.random() * 1.4 - 0.35) * 6200)
    profit += swing
    ev += Math.round(swing * 0.86 + 900)
    const d = new Date(2025, 0, 6 + i * 7)
    out.push({
      week: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      profit,
      ev,
    })
  }
  return out
})()

// bb/100 by stake level
export const stakeBreakdown = [
  { stake: "NL100", hands: 412000, winrate: 8.4, profit: 41800 },
  { stake: "NL200", hands: 388000, winrate: 7.1, profit: 55100 },
  { stake: "NL500", hands: 306000, winrate: 5.9, profit: 48200 },
  { stake: "NL1000", hands: 214000, winrate: 4.2, profit: 31600 },
  { stake: "NL2000", hands: 100000, winrate: 1.8, profit: 8220 },
]

// Pre-flop engine gauges (with healthy ranges)
export interface Metric {
  key: string
  label: string
  value: number
  unit: string
  optimalLow: number
  optimalHigh: number
  note: string
}

export const preflopMetrics: Metric[] = [
  { key: "vpip", label: "VPIP", value: 24.1, unit: "%", optimalLow: 22, optimalHigh: 27, note: "Voluntarily put $ in pot" },
  { key: "pfr", label: "PFR", value: 19.8, unit: "%", optimalLow: 18, optimalHigh: 23, note: "Pre-flop raise" },
  { key: "gap", label: "VPIP–PFR Gap", value: 4.3, unit: "pts", optimalLow: 0, optimalHigh: 5, note: "Passive calling gap" },
  { key: "3bet", label: "3-Bet", value: 8.9, unit: "%", optimalLow: 7, optimalHigh: 11, note: "Re-raise frequency" },
  { key: "fold3bet", label: "Fold to 3-Bet", value: 52.4, unit: "%", optimalLow: 45, optimalHigh: 58, note: "Folding vs re-raise" },
  { key: "steal", label: "Steal Attempt", value: 41.2, unit: "%", optimalLow: 38, optimalHigh: 48, note: "Late position raises" },
]

export const postflopMetrics: Metric[] = [
  { key: "cbet", label: "Flop C-Bet", value: 62.5, unit: "%", optimalLow: 55, optimalHigh: 68, note: "Continuation bet" },
  { key: "foldcbet", label: "Fold to C-Bet", value: 44.8, unit: "%", optimalLow: 40, optimalHigh: 52, note: "Folding vs c-bet" },
  { key: "wwsf", label: "WWSF", value: 47.9, unit: "%", optimalLow: 45, optimalHigh: 52, note: "Won when saw flop" },
  { key: "wsd", label: "W$SD", value: 53.6, unit: "%", optimalLow: 50, optimalHigh: 56, note: "Won $ at showdown" },
  { key: "wtsd", label: "WTSD", value: 27.1, unit: "%", optimalLow: 24, optimalHigh: 30, note: "Went to showdown" },
  { key: "aggr", label: "Aggression Factor", value: 2.8, unit: "x", optimalLow: 2.2, optimalHigh: 3.4, note: "Bets+raises / calls" },
]

// Action distribution by street (bar chart)
export const actionDistribution = [
  { street: "Preflop", fold: 62, call: 14, raise: 24 },
  { street: "Flop", fold: 41, call: 27, raise: 32 },
  { street: "Turn", fold: 38, call: 31, raise: 31 },
  { street: "River", fold: 44, call: 34, raise: 22 },
]

// Villain mapping — who takes the hero's money
export interface Villain {
  id: string
  alias: string
  hands: number
  net: number // negative = villain took money from hero
  vpip: number
  pfr: number
  threeBet: number
  wtsd: number
  style: "TAG" | "LAG" | "Nit" | "Fish" | "Reg" | "Maniac"
  tags: string[]
}

export const villains: Villain[] = [
  { id: "v1", alias: "GTO_Slayer", hands: 8420, net: -14280, vpip: 21, pfr: 18, threeBet: 9.4, wtsd: 26, style: "TAG", tags: ["3-bets light", "tough river"] },
  { id: "v2", alias: "riverRat88", hands: 6110, net: -9840, vpip: 34, pfr: 12, threeBet: 4.1, wtsd: 33, style: "Fish", tags: ["calls too much", "bluff-catches"] },
  { id: "v3", alias: "PolishHammer", hands: 5230, net: -7620, vpip: 28, pfr: 24, threeBet: 12.8, wtsd: 24, style: "LAG", tags: ["over-aggro turn", "capped ranges"] },
  { id: "v4", alias: "quietNit_x", hands: 4970, net: 6210, vpip: 15, pfr: 13, threeBet: 5.2, wtsd: 21, style: "Nit", tags: ["folds to pressure"] },
  { id: "v5", alias: "TiltedTom", hands: 3880, net: 8420, vpip: 41, pfr: 29, threeBet: 15.1, wtsd: 38, style: "Maniac", tags: ["spew on tilt", "target"] },
  { id: "v6", alias: "solverBot99", hands: 7340, net: -3110, vpip: 23, pfr: 20, threeBet: 10.2, wtsd: 27, style: "Reg", tags: ["balanced", "avoid"] },
  { id: "v7", alias: "callingStation", hands: 2960, net: 11240, vpip: 47, pfr: 8, threeBet: 2.3, wtsd: 44, style: "Fish", tags: ["value target", "never folds"] },
  { id: "v8", alias: "eu_grinder", hands: 5610, net: -5320, vpip: 22, pfr: 19, threeBet: 8.8, wtsd: 25, style: "TAG", tags: ["solid", "small edge"] },
  { id: "v9", alias: "shortStackSam", hands: 3410, net: 2180, vpip: 19, pfr: 17, threeBet: 7.1, wtsd: 22, style: "Reg", tags: ["short-stack push"] },
  { id: "v10", alias: "AllInAnnie", hands: 2140, net: 6740, vpip: 52, pfr: 38, threeBet: 19.2, wtsd: 41, style: "Maniac", tags: ["target", "isolate wide"] },
]

// Big pots & river audit
export interface BigHand {
  id: string
  hand: string
  board: string
  potBB: number
  netUSD: number
  position: string
  villain: string
  riverAction: "Value Bet" | "Bluff" | "Call" | "Fold" | "Check"
  result: "won" | "lost"
  stake: string
}

export const bigHands: BigHand[] = [
  { id: "h1", hand: "A♠ K♠", board: "A♦ K♥ 7♣ 2♠ Q♠", potBB: 412, netUSD: 4120, position: "BTN", villain: "riverRat88", riverAction: "Value Bet", result: "won", stake: "NL1000" },
  { id: "h2", hand: "Q♣ Q♦", board: "K♠ 9♦ 4♣ 8♥ K♦", potBB: 388, netUSD: -3880, position: "CO", villain: "GTO_Slayer", riverAction: "Call", result: "lost", stake: "NL1000" },
  { id: "h3", hand: "J♥ T♥", board: "9♥ 8♣ 2♥ 3♦ 7♠", potBB: 356, netUSD: 3560, position: "BB", villain: "PolishHammer", riverAction: "Bluff", result: "won", stake: "NL500" },
  { id: "h4", hand: "A♣ A♦", board: "6♠ 5♠ 4♦ 7♣ 8♦", potBB: 502, netUSD: -5020, position: "SB", villain: "TiltedTom", riverAction: "Call", result: "lost", stake: "NL2000" },
  { id: "h5", hand: "K♦ K♣", board: "K♠ T♦ 3♥ J♣ 2♠", potBB: 444, netUSD: 4440, position: "BTN", villain: "callingStation", riverAction: "Value Bet", result: "won", stake: "NL1000" },
  { id: "h6", hand: "A♥ Q♦", board: "Q♥ 8♠ 5♣ 5♦ A♣", potBB: 298, netUSD: 2980, position: "MP", villain: "eu_grinder", riverAction: "Value Bet", result: "won", stake: "NL500" },
  { id: "h7", hand: "7♠ 7♦", board: "A♦ K♣ Q♠ 2♥ 9♦", potBB: 210, netUSD: -2100, position: "CO", villain: "solverBot99", riverAction: "Fold", result: "lost", stake: "NL500" },
  { id: "h8", hand: "T♣ T♠", board: "J♦ 9♣ 8♥ 7♦ 6♠", potBB: 336, netUSD: -3360, position: "BB", villain: "AllInAnnie", riverAction: "Call", result: "lost", stake: "NL2000" },
]

// River decision efficiency (radar-ish summarised as bars)
export const riverDecisions = [
  { action: "Value Bets", count: 1840, evPerBB: 0.42 },
  { action: "Bluffs", count: 620, evPerBB: 0.18 },
  { action: "Bluff-Catches", count: 980, evPerBB: -0.06 },
  { action: "Folds", count: 2410, evPerBB: 0.11 },
  { action: "Checks", count: 1320, evPerBB: 0.03 },
]

// Population / Mass Data Analysis — how the field plays on average
export interface PopStyle {
  style: string
  share: number
  avgVpip: number
  avgWinrate: number
}

export const populationStyles: PopStyle[] = [
  { style: "Regs (TAG/Reg)", share: 38, avgVpip: 22, avgWinrate: 1.2 },
  { style: "Fish", share: 27, avgVpip: 43, avgWinrate: -14.6 },
  { style: "LAG", share: 14, avgVpip: 30, avgWinrate: -2.1 },
  { style: "Nits", share: 12, avgVpip: 15, avgWinrate: -0.8 },
  { style: "Maniacs", share: 9, avgVpip: 51, avgWinrate: -21.3 },
]

// Population tendencies by position (fold to steal)
export const popFoldToSteal = [
  { pos: "UTG", fold: 74 },
  { pos: "MP", fold: 71 },
  { pos: "CO", fold: 66 },
  { pos: "BTN", fold: 58 },
  { pos: "SB", fold: 61 },
  { pos: "BB", fold: 49 },
]

export const currency = (n: number) =>
  (n < 0 ? "-$" : "$") + Math.abs(n).toLocaleString("en-US")
