import re
import csv
import logging
import datetime

from data_model import *

logger = logging.getLogger(__name__)


class Parser:

    def __init__(self):
        pass

    @property
    def _cur_hand(self):
        return self._game.hands[-1]

    def parse_line(self, row):
        line, time, token = row
        normline = line.lower()
        if "created the game with a stack of" in line or "The admin approved" in line:
            player_name = line.split('"')[1]
            start_amount = float(line.split()[-1][:-1])
            self._game.players_in_for[player_name] = start_amount
        elif line == "entry":
            pass
        elif line.startswith("Undealt cards:"):
            pass
        elif "requested a seat" in line:
            pass
        elif "canceled the seat request" in line:
            pass
        elif "rejected the seat request" in line:
            pass
        elif "changed the ID from" in line:
            pass
        elif "stand up with the stack" in line:
            pass
        elif "sit back with the stack" in line:
            pass
        elif "quits the game with a stack of" in line:
            pass
        elif "joined the game with a stack of" in line:
            pass
        elif "passed the room ownership" in line:
            pass
        elif "queued the stack change for the player" in line:
            pass
        elif "enqueued the removal of the player " in line:
            pass
        elif "updated the player" in line:
            pass
        elif "small blind was changed from" in line:
            pass
        elif "big blind was changed from" in line:
            pass
        elif re.search("The game's ante was changed from ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) to ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)).", line):
            pass
        elif "dead small blind" in normline or "dead big blind" in normline:
            pass
        elif re.search('The admin "(.*)" forced the player ".*" to away mode in the next hand.', line):
            pass
        elif "uncalled bet" in normline:
            match = re.search(r'Uncalled bet of ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) returned to "(.*)"', line)
            uncalled_bet = float(match.group(1))
            self._cur_hand.uncalled_bet = uncalled_bet
        elif re.search("run it twice", line):
            pass
        elif line.startswith("Player stacks:"):
            line = line[len("Player stacks: "):]
            entries = line.split(" | ")
            stack_sizes = [x.strip().rsplit(' ', 1)[1] for x in entries]
            stack_size_counts = [float(x.strip('()')) for x in stack_sizes]
            players = [x.split('"')[1] for x in entries]
            player_amounts = {player: stack_size for (player, stack_size) in zip(players, stack_size_counts)}
            if len(self._game.hands) > 0:
                self._cur_hand.conclude_hand()
            self._game.hands.append(Hand(len(self._game.hands) + 1, datetime.now(), player_amounts))
        elif "-- starting hand" in line:
            if "dead button" in line:
                dealer_name = "None"
            else:
                dealer_name = line.split('"')[1]
        elif line.startswith("Your hand is "):
            cards = line[len("Your hand is "):].split(", ")
        elif " shows a " in line:
            player_name = line.split('"')[1]
            assert line.endswith('.')
            cards = line.split(" shows a ")[1][:-1].split(", ")
            self._cur_hand.show_card(player_name, cards)
        elif "posts a missing small blind of" in line:
            player_name = line.split('"')[1]
            small_blind = float(line.split()[-1])
            self._cur_hand.add_action(Action(player_name, Decision.MISSED_SMALL_BLIND, small_blind))
        elif "posts a small blind of" in line:
            player_name = line.split('"')[1]
            small_blind = float(line.split()[-1])
            self._cur_hand.add_action(Action(player_name, Decision.SMALL_BLIND, small_blind))
        elif "posts a missed big blind of" in line:
            player_name = line.split('"')[1]
            big_blind = float(line.split()[-1])
            self._cur_hand.add_action(Action(player_name, Decision.MISSED_BIG_BLIND, big_blind))
        elif re.search(r'"(.*)" posts a big blind of ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))', line):
            match = re.search(r'"(.*)" posts a big blind of ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))', line)
            player_name = match.group(1)
            big_blind = float(match.group(2))
            self._cur_hand.add_action(Action(player_name, Decision.BIG_BLIND, big_blind))
        elif re.search('"(.*)" posts a straddle of ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))', line):
            match = re.search('"(.*)" posts a straddle of ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))', line)
            player_name = match.group(1)
            straddle = float(match.group(2))
            self._cur_hand.add_action(Action(player_name, Decision.STRADDLE, straddle))
        elif re.search('"(.*)" posts a straddle of ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))', line):
            match = re.search('"(.*)" posts a straddle of ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))', line)
            player_name = match.group(1)
            straddle = float(match.group(2))
            self._cur_hand.add_action(Action(player_name, Decision.STRADDLE, straddle))
        elif line.endswith("folds"):
            player_name = line.split('"')[1]
            self._cur_hand.add_action(Action(player_name, Decision.FOLD))
        elif line.endswith("checks"):
            player_name = line.split('"')[1]
            self._cur_hand.add_action(Action(player_name, Decision.CHECK))
        elif re.search(r'"(.*)" calls ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))$', line):
            match = re.search(r'"(.*)" calls ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))$', line)
            player_name = match.group(1)
            call_amount = float(match.group(2))
            self._cur_hand.add_action(Action(player_name, Decision.CALL, call_amount))
        elif re.search(r'"(.*)" calls ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) and go all ', line):
            match = re.search(r'"(.*)" calls ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) and go all ', line)
            player_name = match.group(1)
            call_amount = float(match.group(2))
            self._cur_hand.add_action(Action(player_name, Decision.CALL, call_amount))
        elif re.search(r'"(.*)" raises to ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))$', line):
            match = re.search(r'"(.*)" raises to ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))$', line)
            player_name = match.group(1)
            raise_amount = float(match.group(2))
            self._cur_hand.add_action(Action(player_name, Decision.RAISE, raise_amount))
        elif re.search(r'"(.*)" raises to ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) and go all ', line):
            match = re.search(r'"(.*)" raises to ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) and go all ', line)
            player_name = match.group(1)
            raise_amount = float(match.group(2))
            self._cur_hand.add_action(Action(player_name, Decision.RAISE, raise_amount))
        elif re.search(r'"(.*)" bets ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))$', line):
            match = re.search(r'"(.*)" bets ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+))$', line)
            player_name = match.group(1)
            raise_amount = float(match.group(2))
            self._cur_hand.add_action(Action(player_name, Decision.BET, raise_amount))
        elif re.search(r'"(.*)" bets ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) and go all ', line):
            # TODO: This is the first bet in a round, should be treated differently
            match = re.search(r'"(.*)" bets ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) and go all ', line)
            player_name = match.group(1)
            raise_amount = float(match.group(2))
            self._cur_hand.add_action(Action(player_name, Decision.BET, raise_amount))
        elif "raises and all in with" in line:
            player_name = line.split('"')[1]
            raise_amount = float(line.split()[-1])
            self._cur_hand.add_action(Action(player_name, Decision.RAISE, raise_amount))
        elif normline.startswith("flop"):
            card_string = line.split('[')[1].split(']')[0]
            cards = card_string.split(', ')
            self._cur_hand.start_new_street(StreetType.FLOP, cards)
        elif normline.startswith("turn (second run):"):
            card = line.split('[')[1].split(']')[0]
        elif normline.startswith("river (second run):"):
            card = line.split('[')[1].split(']')[0]
        elif normline.startswith("turn:"):
            card = line.split('[')[1].split(']')[0]
            self._cur_hand.start_new_street(StreetType.TURN, [card])
        elif normline.startswith("river:"):
            card = line.split('[')[1].split(']')[0]
            self._cur_hand.start_new_street(StreetType.RIVER, [card])
        elif re.search(r'"(.*)" collected ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) from pot$', line):
            match = re.search(r'"(.*)" collected ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) from pot$', line)
            winner_name = match.group(1)
            win_amount = float(match.group(2))
            self._cur_hand.record_winning(winner_name, win_amount)
        elif re.search(r'"(.*)" collected ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) from pot with .* \(combination: (.*)\)', line):
            match = re.search(r'"(.*)" collected ([+-]?([0-9]+\.?[0-9]*|\.[0-9]+)) from pot with .* \(combination: (.*)\)', line)
            winner_name = match.group(1)
            win_amount = float(match.group(2))
            combination = match.group(3)
            winning_hand = combination.split(", ")
            self._cur_hand.record_winning(winner_name, win_amount, combination)
        # elif " collected " in line:  # obsoleted and covered by the previous case?
        #     winner_name = line.split('"')[1]
        #     win_amount = float(line.split()[-1])
        # elif " wins " in line:  # obsoleted?
        #     winner_name, rest = line.split('"')[1:]
        #     amount = float(rest.split()[1])
        #     assert rest.endswith(')')
        #     winning_hand = rest.split("hand: ")[1][:-1].split(", ")
        elif "-- ending hand" in line:
            pass
        else:
            logger.warning(f"Unexpected line found in log: '{line}'. Likely the log format has changed and this script needs to be updated.")

    def parse(self, file_name):
        self._game = Game()
        f = open(file_name, 'r')
        csv_reader = csv.reader(f)
        for row in reversed([row for row in csv_reader]):
            try:
                self.parse_line(row)
            except Exception as e:
                logger.error(f"Error parsing line: {row}.")
                raise e
        return self._game
