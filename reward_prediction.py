import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import deque,defaultdict
import torch.nn.functional as F
import numpy as np


class Tile:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __repr__(self):
        return f"{self.suit} {self.value}"

    def __eq__(self, other):
        return self.suit == other.suit and self.value == other.value
    

class MahjongGame:
    def __init__(self, num_players=4):
        self.num_players = num_players
        self.players = [[] for _ in range(num_players)]
        self.wall = self._create_wall()
        self.discards = [[] for _ in range(num_players)]
        self.current_player = 0
        self.scores = [0] * num_players

    def _create_wall(self):
        suits = ["mans", "pins", "sticks"]
        tiles = [Tile(suit, value) for suit in suits for value in range(1, 10)] * 4 #includes flowers
        honors  = ["東", "南", "西", "北", "白", "發", "中"]
        for i in range(4):
            tiles.extend([Tile(suit, 0) for suit in honors])
        random.shuffle(tiles)
        return tiles

    def deal_tiles(self):
        # Deal 13 tiles to each player
        for _ in range(13):
            for player in self.players:
                player.append(self.wall.pop())

    def draw_tile(self, player):
        # Player draws a tile from the wall
        tile = self.wall.pop()
        self.players[player].append(tile)
        return tile

    def discard_tile(self, player, tile):
        # Player discards a tile
        if tile not in self.players[player]:
            print(f"Error: {tile} not in player's hand!")
            return 
        self.players[player].remove(tile)
        self.discards[player].append(tile)

    def get_game_state(self):
        #current game state
        state = {
            "hand": [sorted(player.copy(), key=lambda x: (x.suit, x.value)) for player in self.players],
            "discards": [sorted(discard.copy(), key=lambda x: (x.suit, x.value)) for discard in self.discards],
            "current_player": self.current_player
        }
        return state
    
    def check_win(self, player):
        # Check if the player's hand is a winning hand
        # Implement winning logic here
        hand = self.players[player]
        if is_winning_hand(hand):
            print(f"Player {player} wins!")
            self.scores[player] += 1000
            return True
        return False
        

    def play_turn(self):
        tile = self.draw_tile(self.current_player)
        print(f"Player {self.current_player} draws {tile}")
        state = self.get_game_state() 
        if self.check_win(self.current_player):
            return True 
        best_tile_to_discard = decide_tile_to_discard(agent, self.get_game_state()) 
        judge, best_tile_to_discard, player = self.can_pong_from_discard(self.current_player, state, best_tile_to_discard, num_players=4, epsilon=0.2)
        while judge:
            judge, best_tile_to_discard, player = self.can_pong_from_discard(player, self.get_game_state(), best_tile_to_discard, num_players=4, epsilon=0.2)
        
        self.discard_tile(player, best_tile_to_discard)
        self.current_player = (player + 1) % self.num_players
        return False, self.current_player  
    

    def can_pong_from_discard(self, current_player, state, discarded_tile, num_players = 4, epsilon=0.2):
        """
        Check if the player can form a Pong (3 identical tiles) using a discarded tile.
        """
        # Count how many of the discarded tile exist in the player's hand
        for player in ((current_player + 1) % num_players, (current_player + 2) % num_players, (current_player + 3) % num_players):
            hand = state['hand'][player]
            count = sum(1 for tile in hand if tile.suit == discarded_tile.suit and tile.value == discarded_tile.value)
            # If the player has two of the discarded tile, they can form a Pong
            if count == 2 and np.random.rand() > epsilon:
                state['hand'][player].append(discarded_tile)
                print(f"Player {player} forms a Pong with {discarded_tile}")
                if self.check_win(player):
                    print(f"Player {player} wins!")
                    return True
                best_tile_to_discard = decide_tile_to_discard(agent, self.get_game_state())#true or false
                return True, best_tile_to_discard, player
        return False, discarded_tile, current_player
        
    
    

def is_straight(tiles):
    """
    Check if the given tiles form a valid straight (chow).
    Tiles must be of the same suit and consecutive in value.
    """
    if len(tiles) != 3:
        return False
    suits = {tile.suit for tile in tiles}
    if len(suits) != 1:  # All tiles must be of the same suit
        return False
    if any(tile.suit == "honors" for tile in tiles):
        return False
    values = sorted([tile.value for tile in tiles])
    return values[0] + 1 == values[1] and values[1] + 1 == values[2]

def is_pon(tiles):
    """
    Check if the given tiles form a valid pung (3 identical tiles).
    """
    if len(tiles) != 3:
        return False
    return all(tile == tiles[0] for tile in tiles)

def is_pair(tiles):
    """
    Check if the given tiles form a valid pair (2 identical tiles).
    """
    if len(tiles) != 2:
        return False
    return tiles[0] == tiles[1]

def find_melds(hand):
    """
    Find all possible melds (straights or pungs) in the hand.
    """
    melds = []
    hand = sorted(hand, key=lambda x: (x.suit, x.value))  # Sort hand for easier processing

    # Check for pungs
    counts = defaultdict(int)
    for tile in hand:
        counts[(tile.suit, tile.value)] += 1
    for key, count in counts.items():
        if count >= 3:
            melds.append([tile for tile in hand if tile.suit == key[0] and tile.value == key[1]][:3])

    # Check for straights
    for i in range(len(hand) - 2):
        group = hand[i:i+3]
        if is_straight(group):
            melds.append(group)

    return melds


def is_winning_hand(hand):
    """
    Check if the hand is a winning hand (4 melds and 1 pair).
    """
    if len(hand) != 14:  # A complete hand has 14 tiles
        return False

    # Find all possible pairs
    counts = defaultdict(int)
    for tile in hand:
        counts[(tile.suit, tile.value)] += 1
    #print(counts)
    test_hand = hand
    for (suit, value), num_times in counts.items():
        test_hand = hand.copy()
        if num_times >= 2:
            test_hand.remove(Tile(suit, value))
            test_hand.remove(Tile(suit, value))
            counts[(suit, value)] -= 2
            if can_form_meld(test_hand):
                return True
            test_hand.append(Tile(suit, value))
            test_hand.append(Tile(suit, value))
            counts[(suit, value)] += 2
    return False

def can_form_meld(hand):
    #Check straights
    if len(hand) == 0:
        return True
    for tile in hand:
        suit = tile.suit
        value = tile.value
        next_value = value + 1
        next_next_value = value + 2
        if 1 <= value <= 7:
            if Tile(suit, next_value) in hand and Tile(suit, next_next_value) in hand:
                hand.remove(Tile(suit, value))
                hand.remove(Tile(suit, next_value))
                hand.remove(Tile(suit, next_next_value))
                if can_form_meld(hand):
                    return True
                hand.append(Tile(suit, value))  # Backtrack
                hand.append(Tile(suit, next_value))
                hand.append(Tile(suit, next_next_value))
        if hand.count(Tile(suit, value)) >= 3:
            hand.remove(Tile(suit, value))
            hand.remove(Tile(suit, value))
            hand.remove(Tile(suit, value))
            if can_form_meld(hand):
                return True
            hand.append(Tile(suit, value))  # Backtrack
            hand.append(Tile(suit, value))
            hand.append(Tile(suit, value))
    return False



'''
def is_winning_hand(hand):
    """
    Check if the hand is a winning hand (4 melds and 1 pair).
    """
    if len(hand) != 14:  # A complete hand has 14 tiles
        return False

    # Find all possible pairs
    counts = defaultdict(int)
    for tile in hand:
        counts[(tile.suit, tile.value)] += 1
    pairs = [key for key, count in counts.items() if count >= 2]

    # Try each pair and see if the remaining tiles can form 4 melds
    for pair_key in pairs:
        remaining_hand = hand.copy()
        # Remove the pair from the hand
        pair_tiles = [tile for tile in remaining_hand if tile.suit == pair_key[0] and tile.value == pair_key[1]][:2]
        for tile in pair_tiles:
            remaining_hand.remove(tile)

        # Find melds in the remaining hand
        melds = find_melds(remaining_hand)
        if len(melds) >= 4:
            return True

    return False
'''
'''
def is_reach_possible(hand):
    """
    Check if the hand is in a state where a player can declare a reach.
    (i.e., the hand is 13 tiles and 1 tile away from being a winning hand)
    """
    if len(hand) != 14: 
        return False
    counts = defaultdict(int)
    for tile in hand:
        counts[(tile.suit, tile.value)] += 1
    pairs = [key for key, count in counts.items() if count >= 2]
    for pair_key in pairs:
        remaining_hand = hand.copy()
        pair_tiles = [tile for tile in remaining_hand if tile.suit == pair_key[0] and tile.value == pair_key[1]][:2]
        for tile in pair_tiles:
            remaining_hand.remove(tile)
        melds = find_melds(remaining_hand)
        if len(melds) == 4:
            return True

    return False
# Example usage
'''




class GlobalRewardPredictor(nn.Module):
    def __init__(self, input_size):
        super(GlobalRewardPredictor, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 1)
        self.relu = nn.ReLU()

    def forward(self, state):
        x = self.relu(self.fc1(state))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x


def pair_count(hand):
    pair_count = 0
    counts = defaultdict(int)
    for tile in hand:
        counts[(tile.suit, tile.value)] += 1
    for count in counts.values():
        if count >= 2:
            pair_count += 1
    return pair_count


def discard_count(state, drawn_tile):
    discard_count = 0
    for player_discard in state["discards"]:
        for tile in player_discard:
            if tile.value == drawn_tile.value and tile.suit == drawn_tile.suit:
                discard_count += 1  
    return discard_count



def look_ahead_features(state, player, drawn_tile):#deciding which tile to discard
    features = []
    features.append(len(find_melds(state['hand'][player])))#adding current player's melds' number to features
    features.append(pair_count(state['hand'][player]))##adding current player's pair's number to features
    features.append(discard_count(state, drawn_tile))#adding number of discarded tiles same as drawn_tile to features

    return torch.FloatTensor(features)

def decide_tile_to_discard(agent, state):
    hand = state["hand"][state["current_player"]]#current player hand    
    best_tile = None
    best_value = -float("inf")  
 
    for tile in hand:
        state_features = look_ahead_features(state, state["current_player"], drawn_tile=tile)
        predicted_value = agent.predict_reward(state_features).item()
        
        if predicted_value > best_value:
            best_value = predicted_value
            best_tile = tile
    
    if best_tile not in hand:
        print(f"Error: {best_tile} not found in player's hand!")
        return None
    return best_tile



class GlobalRewardAgent:
    def __init__(self, input_size, learning_rate=0.001):
        self.model = GlobalRewardPredictor(input_size)
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()

    def predict_reward(self, state_features):
        return self.model(state_features)

    def train(self, state, true_reward, drawn_tile):
        self.optimizer.zero_grad()
        state_features = look_ahead_features(state, state['current_player'], drawn_tile)
        predicted_reward = self.predict_reward(state_features)#input state_features into NN
        loss = self.criterion(predicted_reward, torch.FloatTensor([true_reward]))
        loss.backward()
        self.optimizer.step()
        return loss.item()
    

    def calculate_reward(self, state, action, player, drawn_tile, is_win=False):
        """
        Calculate the reward based on the current state and the action taken.
        """
        reward = 0
        player_hand = state['hand'][player]
        # Winning reward
        if is_win:
            reward += 1000  # Reward for winning the game
        
        # Reward for forming a Pong or Chow
        if action == "Pong" and is_pon(player_hand):
            reward += 100  # Reward for forming a Pong
        elif action == "Chow" and can_chow_from_discard(player_hand, drawn_tile):
            reward += 50  # Reward for forming a Chow
        
        # Penalty for discarding important tiles (e.g., if a tile is essential for completing a hand)
        if action == "Discard" and self.is_important_tile(drawn_tile, player_hand):
            reward -= 100  # Penalty for discarding a critical tile
        
        # Small penalty for taking too long to make a decision
        reward -= 5  # A small penalty for taking a longer turn (to encourage efficiency)
        
        return reward

    def is_important_tile(self, tile, hand):
        """
        Determine if a tile is critical for completing the hand.
        This can be based on the strategy, such as if a tile is required to complete a set.
        """
        # A simplistic approach: check if the tile completes a potential meld
        for meld in find_melds(hand):
            for tile_in_meld in meld:
                if tile_in_meld == tile:
                    return False  # If the tile is already part of a meld, it's not important to discard
        
        # If the tile is not part of any meld, it might be important
        return True

agent = GlobalRewardAgent(input_size=3)
'''
def can_pong_from_discard(current_player, state, discarded_tile, num_players = 4):
    """
    Check if the player can form a Pong (3 identical tiles) using a discarded tile.
    """
    # Count how many of the discarded tile exist in the player's hand
    for player in ((current_player + 1) % num_players, (current_player + 2) % num_players, (current_player + 3) % num_players):
        hand = state['hand'][player]
        count = sum(1 for tile in hand if tile.suit == discarded_tile.suit and tile.value == discarded_tile.value)
         # If the player has two of the discarded tile, they can form a Pong
        if count == 2:
            state['hand'][player].append(discarded_tile)
            print(f"Player {player} forms a Pong with {discarded_tile}")
            if MahjongGame.check_win(player):
                print(f"Player {player} wins!")
                return True
            best_tile_to_discard = decide_tile_to_discard(agent, MahjongGame.get_game_state())#true or false
            return True, best_tile_to_discard, player
    return False, discarded_tile, current_player
'''    
    
    
   

def can_chow_from_discard(hand, discarded_tile):
    """
    Check if the player can form a Chow (consecutive 3 tiles of the same suit) using a discarded tile.
    """
    if discarded_tile.suit == "honors":
        return False  # Honors tiles cannot form a Chow
    
    # Group the hand by suit and check if we can form a Chow with the discarded tile
    grouped_by_suit = defaultdict(list)
    for tile in hand:
        if tile.suit != "honors":  # Honors tiles can't form a Chow
            grouped_by_suit[tile.suit].append(tile.value)

    # For each suit, check if a Chow can be formed with the discarded tile
    for suit, values in grouped_by_suit.items():
        if discarded_tile.suit == suit:
            values.append(discarded_tile.value)  # Add the discarded tile
            values.sort()  # Sort the values to check for sequences
            
            # Look for a sequence of 3 consecutive tiles
            for i in range(len(values) - 2):
                if values[i] + 1 == values[i + 1] and values[i + 1] + 1 == values[i + 2]:
                    return True  # Found a valid Chow
    return False


    
def extract_features(state, player, discarded_tile):

    features = []
    features.append(state["current_player"])
  
    current_player_hand = state["hand"][state["current_player"]]
    melds = find_melds(current_player_hand)
    features.append(len(melds)) 
    
    can_pong = False
    if can_pong:
        features.append(can_pong)  #whether we can pong
        
    can_chow = False
    if can_chow:
            features.append(can_chow)
      #whether we can chow  
    return torch.FloatTensor(features)

def decide_action(agent, state, discarded_tile):
    state_features = extract_features(state, discarded_tile)
    action_values = agent.predict_action(state_features).detach().numpy()  #predicted action value

    action = np.argmax(action_values)
    return action#pong or chow