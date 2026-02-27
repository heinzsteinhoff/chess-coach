"""King's Indian Defense opening data — main lines and strategic ideas."""

KID_LINES = [
    {
        "name": "Classical Variation",
        "eco": "E90-E99",
        "moves": "1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5",
        "key_fen": "rnbq1rk1/ppp1ppbp/3p1np1/4P3/2PPP3/2N2N2/PP2BPPP/R1BQK2R w KQ - 0 7",
        "ideas": {
            "black": [
                "Establish the e5 pawn as a strongpoint",
                "Prepare the kingside attack with ...Nh5, ...f5",
                "After d5, attack on the kingside with ...f5-f4, ...g5, ...Rf7-g7",
                "The Bg7 becomes a monster after ...f5 and the kingside opens",
            ],
            "white": [
                "Close the center with d5 and expand on the queenside (c5, b4, a4)",
                "Or maintain tension with Bg5 or d5 alternatives",
                "Queenside space advantage and potential passed c-pawn",
                "Try to keep the kingside closed while breaking through on the queenside",
            ],
        },
        "critical_positions": [
            {
                "fen": "r1bq1rk1/ppp2pbp/2np1np1/4p3/2PPP3/2N1BN2/PP2BPPP/R2QK2R w KQ - 0 8",
                "after": "7. d5 Nc6 8. Be3",
                "theme": "The Mar del Plata Attack setup. Black will play ...Nh5, ...f5.",
            },
            {
                "fen": "r1bq1rk1/ppp2pbp/3p1np1/3Pp3/2P1P3/2N1BN2/PP2BPPP/R2QK2R b - - 0 8",
                "after": "7. d5 Nc6 8. Be3 (Classical main line)",
                "theme": "Black must decide: ...Nh5 (preparing ...f5) or ...Ne8 (slower but flexible).",
            },
        ],
    },
    {
        "name": "Sämisch Variation",
        "eco": "E80-E89",
        "moves": "1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. f3",
        "key_fen": "rnbqkb1r/ppp1ppbp/3p1np1/8/2PPP3/2N2P2/PP4PP/R1BQKBNR b KQkq - 0 5",
        "ideas": {
            "black": [
                "Play ...c5 for a Benoni-type structure, or ...e5 for classical KID",
                "...a6 and ...b5 for queenside counterplay",
                "The f3 pawn weakens White's kingside slightly",
                "Look for ...f5 breaks when the center is closed",
            ],
            "white": [
                "f3 supports the e4 pawn solidly",
                "Plan Be3, Qd2, O-O-O for opposite-side castling attacks",
                "The Sämisch is aggressive — White aims for a kingside pawn storm too",
                "g4, h4 pushes can create attacking chances",
            ],
        },
        "critical_positions": [],
    },
    {
        "name": "Four Pawns Attack",
        "eco": "E76-E79",
        "moves": "1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. f4",
        "key_fen": "rnbqkb1r/ppp1ppbp/3p1np1/8/2PPPP2/2N5/PP4PP/R1BQKBNR b KQkq - 0 5",
        "ideas": {
            "black": [
                "White is overextended — look for central counterplay with ...c5 or ...e5",
                "After ...O-O and ...c5, the d4 pawn can become a target",
                "Tactical opportunities arise from White's aggressive but loose pawn structure",
                "...e5 followed by ...exf4 can expose White's center",
            ],
            "white": [
                "Maximum central control with four pawns on c4, d4, e4, f4",
                "Crush Black before counterplay develops",
                "The position is sharp — White must maintain the initiative",
                "Development speed is critical",
            ],
        },
        "critical_positions": [],
    },
    {
        "name": "Fianchetto Variation",
        "eco": "E60-E69",
        "moves": "1. d4 Nf6 2. c4 g6 3. Nf3 Bg7 4. g3 O-O 5. Bg2 d6",
        "key_fen": "rnbq1rk1/ppp1ppbp/3p1np1/8/2PP4/5NP1/PP2PPBP/RNBQK2R w KQ - 0 6",
        "ideas": {
            "black": [
                "Play ...c5 to challenge d4 (more common than ...e5 in this line)",
                "After ...c5 and ...Nc6, Black gets a solid position with good piece play",
                "...e5 is also possible but leads to different structures",
                "The Bg2 and Bg7 face each other — whoever controls the long diagonal wins",
            ],
            "white": [
                "Solid, positional approach — no weaknesses",
                "Control the center with pieces rather than pawns",
                "Nc3, e4 to build a classical center, or Qc2 and Rd1 for a slower buildup",
                "Less tactical than other variations — positional understanding is key",
            ],
        },
        "critical_positions": [],
    },
    {
        "name": "Averbakh Variation",
        "eco": "E73-E75",
        "moves": "1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Be2 O-O 6. Bg5",
        "key_fen": "rnbq1rk1/ppp1ppbp/3p1np1/6B1/2PPP3/2N5/PP2BPPP/R2QK1NR b KQ - 0 6",
        "ideas": {
            "black": [
                "...c5 or ...e5 — timing is critical with the Bg5 pin/pressure",
                "...h6 to challenge the bishop is double-edged",
                "...Na6 followed by ...e5 is a common approach",
                "The Bg5 controls f6 and e7 — Black needs to find the right plan",
            ],
            "white": [
                "Bg5 prevents ...e5 in some lines (after ...e5, Bxf6 disrupts Black)",
                "Flexible — can transpose to various setups",
                "Qd2 + O-O-O for aggressive play, or Nf3 + O-O for classical",
                "The bishop pair can be a long-term advantage",
            ],
        },
        "critical_positions": [],
    },
]
