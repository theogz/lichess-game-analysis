import requests
import os
import json
import pendulum
import re
import pandas

LICHESS_API_KEY = os.getenv('LICHESS_API_KEY')
USERNAME = '[lichess user name]'
URL = f'https://lichess.org/api/games/user/{USERNAME}'
PERFORMANCE = 'bullet'
HEADERS = {
    'Authorization': f'Bearer {LICHESS_API_KEY}',
    'Accept': 'application/x-ndjson'
}
EVAL_PGN_REGEX = r'(\[%eval (.*?)\])'
CLOCK_PGN_REGEX = r'(\[%clk (\d+:\d+:\d+)\])'

PARAMETERS = {
    'rated': 'true',
    'perfType': PERFORMANCE,
    'pgnInJson': 'true',
    'clocks': 'true',
    'evals': 'true'
}


def get_last_moves(pgn_text):
    pgn_list = pgn_text.split('\n')
    pgn = next(filter(lambda x: x.startswith('1.'), pgn_list), True)
    raw_moves = re.split(r'\d+\.\s', pgn)
    formatted_moves = []
    last_white_move = ''
    last_black_move = ''
    last_eval_move = ''

    for raw_move in raw_moves:
        if not bool(raw_move):
            continue
        move_list = re.split(r'\d+\.\.\.\s', raw_move)
        last_white_move = move_list[0]
        formatted_move = {
            'white': last_white_move
        }
        if re.search(EVAL_PGN_REGEX, move_list[0]) is not None:
            last_eval_move = move_list[0]
        if len(move_list) >= 2:
            last_black_move = move_list[1]
            formatted_move['black'] = last_black_move
            if re.search(EVAL_PGN_REGEX, move_list[1]) is not None:
                last_eval_move = move_list[1]
        formatted_moves.append(formatted_move)

    return {
        'white': last_white_move,
        'black': last_black_move,
        'last_eval_move': last_eval_move
    }


r = requests.get(URL, headers=HEADERS, params=PARAMETERS)

request_result = r.text

parsed_games = []

# Last game is an empty string, we pop it.
raw_games = request_result.split('\n')[:-1]

for num, game_text in enumerate(raw_games):
    game = json.loads(game_text)
    last_moves = get_last_moves(game['pgn'])
    last_eval_move = last_moves.get('last_eval_move', '')
    last_eval_search = re.search(EVAL_PGN_REGEX, last_eval_move)

    # Relevant props:
    game_id = game['id']
    my_pos = 'white' if game['players']['white']['user']['name'] == USERNAME else 'black'
    victory = my_pos == game.get('winner')
    outcome = game['status']
    result = 'victory' if victory else 'draw' if outcome in ['stalemate', 'draw'] else 'defeat'
    game_date = pendulum.from_timestamp(game['createdAt']/1000).to_iso8601_string()
    white_time_left = re.search(CLOCK_PGN_REGEX, last_moves.get('white', '')).group(2)
    black_time_left = re.search(CLOCK_PGN_REGEX, last_moves.get('black', '')).group(2)
    last_white_move = last_moves.get('white', '')
    last_black_move = last_moves.get('black', '')
    last_eval = last_eval_search.group(2) if bool(last_eval_search) else None

    formatted_props = {
        'game_id': game_id,
        'my_pos': my_pos,
        'outcome': outcome,
        'result': result,
        'game_date': game_date,
        'last_white_move': last_white_move,
        'last_black_move': last_black_move,
        'white_time_left': white_time_left,
        'black_time_left': black_time_left,
        'last_eval': last_eval,
    }
    parsed_games.append(formatted_props)

pandas.DataFrame(
    parsed_games).to_csv(f'lichess - {USERNAME} - {PERFORMANCE}.csv', index=False, sep=',')
