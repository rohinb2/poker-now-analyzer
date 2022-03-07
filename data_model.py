import attr
import copy
import logging
import math

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

def float_eq(a, b):
    if a == None == b:
        return True
    return abs(a - b) < 0.001

def float_gt(a, b):
    return a - b >= 0.001

class Decision(Enum):
    FOLD = 1
    BET = 2
    CALL = 3
    RAISE = 4
    BIG_BLIND = 5
    STRADDLE = 6
    CHECK = 7
    SMALL_BLIND = 8
    MISSED_SMALL_BLIND = 9
    MISSED_BIG_BLIND = 10


@attr.s(auto_attribs=True)
class Action:
    player: str
    decision: Decision
    amount: Optional[float] = None

    def __str__(self):
        if self.decision in [Decision.FOLD, Decision.CHECK]:
            return f"Player: {self.player} took action {self.decision}." 
        return f"Player: {self.player} took action {self.decision} for amount {self.amount}."

class StreetType(Enum):
    PREFLOP = 1
    FLOP = 2
    TURN = 3
    RIVER = 4

@attr.s(auto_attribs=True, init=False)
class Street:
    street_type: StreetType
    actions: List[Action]
    community_cards: List[str]
    starting_pot_value: float
    money_in_per_player: Dict[str, float]
    # Don't want pot value to include an uncalled bet/raise
    uncalled_bet: Optional[Tuple[str, float]] = None
    _bet_facing: Optional[float] = None
    missed_small_blind: Optional[Action] = None

    def __init__(self, street_type: StreetType, actions: List[Action], community_cards: List[str], starting_pot_value: float = 0):
        self.street_type = street_type
        self.actions = actions
        self.community_cards = community_cards
        self.starting_pot_value = starting_pot_value
        self.money_in_per_player = {}
        self.uncalled_bet = None
        self._bet_facing = None
        self.missed_small_blind = None

    def add_action(self, action: Action):
        self.actions.append(action)

        if action.decision == Decision.MISSED_SMALL_BLIND:
            self.missed_small_blind = action
            return
            
        if action.amount is not None:
            # Small blind functionally is a bet, a bet's money is not part of the pot till there's at least one call.
            if self._bet_facing is None:
                self.uncalled_bet = (action.player, action.amount)
                self._bet_facing = action.amount

            # Big blind and straddle are functionally raises
            elif float_gt(action.amount, self._bet_facing):

                # First, ensure that the original betting player's money is now committed to the pot, if no one else has called yet
                if self.uncalled_bet is not None:
                    betting_player, _ = self.uncalled_bet
                    self.money_in_per_player[betting_player] = self._bet_facing
                    self.uncalled_bet = None

                # Then, commit the "calling" portion of the raisers money to the pot, and update the uncalled_bet and bet facing values
                self.money_in_per_player[action.player] = self._bet_facing
                raise_amount = action.amount - self._bet_facing
                self.uncalled_bet = (action.player, raise_amount)
                self._bet_facing = action.amount
            
            elif float_eq(action.amount, self._bet_facing):
                # The uncalled bet value is the *additional* amount they bet. So, we use the call value to determine what their actual money invested is.

                # If no one else has yet called, commit the uncalled bet value to the pot
                if self.uncalled_bet is not None:
                    betting_player, _ = self.uncalled_bet
                    self.money_in_per_player[betting_player] = action.amount
                    self.uncalled_bet = None

                self.money_in_per_player[action.player] = action.amount

            else:
                # The call value is less than the uncalled bet value (the player calling is going all in)
                
                # If no one else has yet called, commit the portion of the uncalled bet to the pot that the player is calling
                if self.uncalled_bet is not None:
                    betting_player, _ = self.uncalled_bet
                    self.money_in_per_player[betting_player] = action.amount
                    self.uncalled_bet = (betting_player, self._bet_facing - action.amount)

                self.money_in_per_player[action.player] = action.amount


    @property
    def final_pot_value(self):
        return self.starting_pot_value + sum([v for _, v in self.money_in_per_player.items()])
    
    @property
    def uncalled_bet_value(self):
        if self.uncalled_bet is not None:
            player, uncalled_amount = self.uncalled_bet
            return uncalled_amount
        return None

    def __str__(self):
        to_print = [str(self.street_type), f"Community cards are {self.community_cards}."]
        to_print.extend([str(a) for a in self.actions])
        to_print.append(f"Final pot value for this street is: {self.final_pot_value}.")
        to_print.append("")
        return '\n'.join(to_print)


@attr.s(auto_attribs=True, init=False)
class Hand:
    start_time: datetime
    streets: List[Street]
    starting_stacks: Dict[str, float]
    winnings: Dict[str, Tuple[float, str]]
    uncalled_bet: Optional[float]
    shown_cards: Dict[str, List[str]]

    def __init__(self, start_time: datetime, starting_stacks: Dict[str, float]):
        logger.info("called")
        self.start_time = start_time
        self.starting_stacks = starting_stacks
        self.streets = [Street(StreetType.PREFLOP, [], [])]
        self.winnings = {}
        self.uncalled_bet = None
        self.shown_cards = {}
        
    @property
    def final_hand_value(self):
        return self.streets[-1].final_pot_value

    def start_new_street(self, street_type: StreetType, new_community_cards: List[str]):
        previous_street = self.streets[-1]
        community_cards = copy.copy(previous_street.community_cards)
        community_cards.extend(new_community_cards)
        self.streets.append(Street(
            street_type=street_type, 
            actions=[], 
            starting_pot_value=previous_street.final_pot_value, 
            community_cards=community_cards)
        )
    
    def contains_player(self, player: str):
        return player in self.starting_stacks
    
    def player_voluntarily_puts_money_in_preflop(self, player: str):
        preflop_street = self.streets[0]
        if player in preflop_street.money_in_per_player:
            for action in preflop_street.actions:
                # does straddle count?
                if action.decision in [Decision.BET, Decision.CALL, Decision.RAISE, Decision.STRADDLE]:
                    return True
        return False
    
    def player_preflop_raises(self, player: str):
        preflop_street = self.streets[0]
        if player in preflop_street.money_in_per_player:
            for action in preflop_street.actions:
                if action.decision == Decision.RAISE:
                    return True
        return False
    
    def show_card(self, player: str, cards: List[str]):
        self.shown_cards[player] = cards
    
    def add_action(self, action: Action):
        self.streets[-1].add_action(action)
    
    def record_winning(self, player: str, amount: float, combination: str = ""):
        self.winnings[player] = (amount, combination)

    def conclude_hand(self):
        starting_table_total = 0
        for _, v in self.starting_stacks.items():
            starting_table_total += v
        
        # Play out finances per hand and ensure it aligns
        ending_stacks = copy.copy(self.starting_stacks)
        for street in self.streets:
            for player, v in street.money_in_per_player.items():
                ending_stacks[player] -= v
            
        for player, (v, _) in self.winnings.items():
            ending_stacks[player] += v
        
        for _, v in ending_stacks.items():
            starting_table_total -= v
        
        if self.streets[0].missed_small_blind is not None:
            starting_table_total += self.streets[0].missed_small_blind.amount

        # Poker now processes an uncalled raise as a call, followed by an uncalled bet
        # This conflicts with the way the info is stored here, correct for this
        internal_uncalled_bet_value = None
        for s in self.streets:
            if s.uncalled_bet_value is not None:
                internal_uncalled_bet_value = s.uncalled_bet_value
    
        if ((internal_uncalled_bet_value is None) != (self.uncalled_bet is None)) or not float_eq(self.uncalled_bet, internal_uncalled_bet_value):
            logger.error("Uncalled bet values don't align.")
            raise Exception("Uncalled bet values don't align")
        
        if not float_eq(starting_table_total, 0.0):
            logger.error("Hand winnings don't align.")
            raise Exception("Hand winnings don't align")


    def __str__(self):
        to_print = [f"The players start the hand with stacks at time {self.start_time}: "]
        to_print.extend([f"{p} : {v}" for p, v in self.starting_stacks.items()])
        to_print.append("")
        to_print.extend([str(s) for s in self.streets])
        to_print.append("The winners of the hand are as follows: ")
        to_print.extend([f"{p} wins {v} with combination {combination}." for p, (v, combination)  in self.winnings.items()])
        to_print.append("")
        if self.shown_cards != {}:
            to_print.append("Players showed hands of: ")
            to_print.extend([f"{p} shows {h}." for p, h in self.shown_cards.items()])
        return '\n'.join(to_print)


@attr.s(auto_attribs=True)
class Game:
    hands: List[Hand] = []
    players_in_for: Dict[str, float] = {}
    players_out_for: Dict[str, float] = {}

    def __str__(self):
        to_print = ["Players were in for: "]
        to_print.extend([f"Player {p} in for {v}" for p, v in players_in_for.items()])
        to_print.append("", "Players were out for: ")
        to_print.extend([f"Player {p} out for {v}" for p, v in players_out_for.items()])
        return '\n'.join(to_print)




