from src.parser.tokenizer import GGPokerTokenizer

# A mão que você forneceu, colada como uma string bruta
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
Seat 1: db22980c (button) folded before Flop (didn't bet)
Seat 2: Hero (small blind) folded before Flop
Seat 3: 3d3afbef (big blind) folded before Flop
Seat 4: a56c444f showed [Kh Ts] and lost with a flush Queen high
Seat 5: 2ab6828d folded before Flop (didn't bet)
Seat 6: 3eeb7226 showed [Js 8s] and won ($0.88) with a flush Queen high
"""

def main():
    tokenizer = GGPokerTokenizer()
    
    print("Iniciando o Parsing de Eventos (Camada Pydantic)...\n")
    
    for line in raw_hand_text.strip().split('\n'):
        event = tokenizer.parse_line(line)
        if event:
            # Imprimimos o evento Pydantic gerado
            print(event)

if __name__ == "__main__":
    main()