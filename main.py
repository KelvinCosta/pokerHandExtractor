from src.parser.tokenizer import GGPokerTokenizer
from src.fsm.states import InitState
from src.etl.loader import HandLoader

# A mão bruta que vamos extrair
raw_hand_text = """
Poker Hand #RC4095246938: Hold'em No Limit ($0.01/$0.02) - 2025/12/03 12:11:28
Table 'RushAndCash36790234' 6-max Seat #1 is the button
Seat 1: db22980c ($3.83 in chips)
Seat 2: Hero ($0.66 in chips)
Seat 3: 3d3afbef ($2.67 in chips)
Seat 4: a56c444f ($1.03 in chips)
Seat 5: 2ab6828d ($2.43 in chips)
Seat 6: 3eeb7226 ($1.47 in chips)
Hero: posts small blind $0.01
3d3afbef: posts big blind $0.02
*** HOLE CARDS ***
Dealt to db22980c 
Dealt to Hero [4h Jh]
Dealt to 3d3afbef 
Dealt to a56c444f 
Dealt to 2ab6828d 
Dealt to 3eeb7226 
a56c444f: raises $0.02 to $0.04
2ab6828d: folds
3eeb7226: calls $0.04
db22980c: folds
Hero: folds
3d3afbef: folds
*** FLOP *** [Qs 2h 9s]
a56c444f: checks
3eeb7226: bets $0.06
a56c444f: calls $0.06
*** TURN *** [Qs 2h 9s] [6s]
a56c444f: checks
3eeb7226: bets $0.12
a56c444f: calls $0.12
*** RIVER *** [Qs 2h 9s 6s] [5s]
a56c444f: checks
3eeb7226: bets $0.24
a56c444f: calls $0.24
3eeb7226: shows [Js 8s] (a flush Queen high)
a56c444f: shows [Kh Ts] (a flush Queen high)
*** SHOWDOWN ***
3eeb7226 collected $0.88 from pot
*** SUMMARY ***
Total pot $0.95 | Rake $0.04 | Jackpot $0.03 | Bingo $0 | Fortune $0 | Tax $0
Board [Qs 2h 9s 6s 5s]
"""

def main():
    tokenizer = GGPokerTokenizer()
    current_state = InitState()
    hand_context = None
    
    # Lista para simular o acúmulo de mãos processadas
    finished_hands = []
    
    print("Iniciando o Processamento Completo (Tokenizador -> FSM)...\n")
    
    for line in raw_hand_text.strip().split('\n'):
        token = tokenizer.parse_line(line)
        if token:
            current_state, hand_context = current_state.process(token, hand_context)

    # Adicionamos a mão finalizada à nossa lista
    if hand_context:
        finished_hands.append(hand_context)

    print("Iniciando a carga no Polars (ETL - Camada Silver)...\n")
    
    # Passa a lista de mãos para o Loader processar
    loader = HandLoader()
    df = loader.process_and_save(finished_hands)
    
    print("\n=== SCHEMA INFERIDO PELO POLARS ===")
    print(df.schema)
    
    print("\n=== PREVIEW DO DATAFRAME (Aninhado) ===")
    print(df)

if __name__ == "__main__":
    main()