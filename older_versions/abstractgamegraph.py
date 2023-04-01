"""Code for the game graph"""
from __future__ import annotations
from typing import Optional
from genreselector import GenreSelector
import tkinter as tk
import csv
import json


class Game:
    """A steam game and its various attributes
    Instance Attributes:
    - name:
        The name of the game.
    - game_id:
        The id of the game.
    - date_release:
        The date for when the game was released.
    - operating_systems:
        A dictionary consisting of a mapping between various operating systems and the game's
        compatibility with them.(str : bool)
    - price:
        the price of the game, in US dollars.
    - positive_ratio:
        An official ratio for the game. It is used in part of our metascore calculation.
    - rating:
        The metascore of the game, which is dependent on the relationship between the game's attributes and the
        user's preferences.
    """
    name: str
    game_id: int  # added
    genres: list[str]
    date_release: str  # swap it to str, make it easier to load
    operating_systems: dict[str, bool]
    price: float
    positive_ratio: int
    rating: Optional[float]  # meta-score

    def __init__(self, name: str, game_id: int, genres: list[str], date: str, operating_system: dict,
                 price: float, positive_ratio: int, rating: float) -> None:
        """Initializes the game instance"""
        self.name = name
        self.game_id = game_id
        self.genres = genres
        self.date_release = date
        self.operating_systems = operating_system
        self.price = price
        self.positive_ratio = positive_ratio
        self.rating = rating

    def genre_count(self, user_genres: list[str]) -> int:
        """Counts the number of user preferenced genres and the game genres that are similar"""
        return len(self.genre_list(user_genres))

    def same_num_game(self, other_game: Game, total_needed: int) -> bool:
        """Compares self to another game and determines if they have a certain number of games, depending on what is
        inputted into the total_needed paramter
        Preconditions:
        - total_needed >= 0
        """
        other_game_genres = other_game.genres
        return self.genre_count(other_game_genres) >= total_needed

    def genre_list(self, genre_collection: list[str]) -> list[str]:
        """Returns a list of all the similar genres between self and the given genre collection"""
        list_so_far = []
        for genre in self.genres:
            if genre in genre_collection:
                list_so_far.append(genre)
        return list_so_far


class GameNode:
    """A node in a game graph"""
    game: Game
    neighbours: list[GameNode]

    def __init__(self, game: Game) -> None:
        """Intializes the game node"""
        self.game = game
        self.neighbours = []

    def top_similar_games(self, total: int) -> list[Game]:
        """Returns a list of at most 'total' length containing the most similar games of genre to self.game. This
        can help to provide game recommendations based on a single game.
        Preconditions:
        - total >= 0
        """
        return self._helper_top_similar_games(total, set())

    def _helper_top_similar_games(self, total: int, visited_so_far: set[Game]) -> list[Game]:
        """Returns a list of at most 'total' length containing the most similar games of genre to self.game
        Doesn't visit any games included in 'visited_so_far'
        Preconditions:
        - total >= 0
        """
        if total > len(self.neighbours):
            total = len(self.neighbours)
        if total == 0:
            return []
        else:
            list_so_far = []
            max_genres_so_far = 0
            most_similar_game = None
            for neighbour in self.neighbours:
                total_genres = self.game.genre_count(neighbour.game.genres)
                if neighbour.game not in visited_so_far and total_genres > max_genres_so_far:
                    most_similar_game = neighbour.game
            list_so_far.append(most_similar_game)
            visited_so_far.add(most_similar_game)
            return list_so_far + self._helper_top_similar_games(total - 1, visited_so_far)

    def has_genre(self, genre: str) -> bool:
        """Determines if the game in this game node has a specific genre."""
        return genre in self.game.genres


class AbstractGameGraph:
    """A graph containing nodes that represent a game. Nodes are connected depending on the number of genres that they
    have in common with another game and the user's preferred genres.
    NOTE:
    - the min_genres_game and min_genres_edge were added in order to create a purpose of the graph data structure.
    Otherwise, we are solely using the nodes for their scores, which does not take advantage of the edges formed between
    nodes. Thus, the min_genres_game and min_genres_edge can be used as a way of filtering
    Representation Invariants:
    - all(self._nodes[game_id].game_id = game_id for game_id in self_nodes)
    """
    #  Private Instance Attibutes:
    #  - _nodes: A mapping from game ids to GameNode objects in the GameGraph.

    _nodes: dict[int, GameNode]

    def __init__(self) -> None:
        """Initializes the game graph"""
        self._nodes = {}

    def add_game(self, game: Game) -> None:
        """Adds a game node into the graph if they have the minimum amount of intersecting genres with the
        user (i.e. self.min_genres_game)"""
        raise NotImplementedError

    def add_edge(self, game1: GameNode, game2: GameNode) -> None:
        """Creates an edge between two game nodes if they have the minimum amount of intersecting genres
        Preconditions:
        - game1 in self._nodes and game2 in self._nodes
        """
        raise NotImplementedError

    def top_games(self, total: int, recorded_games: set[Game]) -> list[Game]:
        """Returns a list of the top recommended games depending on the inputted parameter
        Preconditions:
        - total >= 0
        """
        if total == 0:
            return []
        else:
            list_so_far = []
            max_game = None
            max_score_so_far = 0
            for game in self._nodes:
                node = self._nodes[game]
                if node.game not in recorded_games and node.game.rating > max_score_so_far:
                    max_game = node.game
                    max_score_so_far = node.game.rating
            recorded_games.add(max_game)
            list_so_far.append(max_game)
            rec_result = self.top_games(total - 1, recorded_games)
            return list_so_far + rec_result

    def node_list(self) -> list[GameNode]:
        """Returns a list of all the game nodes in self"""
        list_so_far = []
        for game_id in self._nodes:
            list_so_far.append(self._nodes[game_id])
        return list_so_far


class SimilarGameGraph(AbstractGameGraph):
    """Game graph that is formed based specifically based on the games that the user has inputted.
    Instances Attributes:
    - min_genres_edge is the amount of similar genres that the games of two game nodes must have in order for an edge
    to be formed between them.
    - user_game is a list of games that the user has provided in order to make recommendations.
    Representation Invariants:
    - self.user_game != []
    . self.min_genres_edge >= 0
    """
    min_genres_edge: int
    user_game: list[str]

    def __init__(self, user_game: list[str], similar_genres: int) -> None:
        """Initializes the graph"""
        AbstractGameGraph.__init__(self)
        self.min_genres_edge = similar_genres
        self.user_game = user_game

    def add_game(self, game: Game) -> None:
        """Adds a game into the graph"""
        game_id = game.game_id
        self._nodes[game_id] = GameNode(game)

    def add_edge(self, game1: GameNode, game2: GameNode) -> None:
        """Creates an edge between two nodes in the graph"""
        similar_games = game1.game.genre_count(game2.game.genres)
        if similar_games >= self.min_genres_edge:
            game1.neighbours.append(game2)
            game2.neighbours.append(game1)


class SimilarGenreGraph(AbstractGameGraph):
    """Game graph that is formed specifically based on the genres that the user has inputted
    Instance Attributes:
    - min_genres_game is the minimum number of genres that a game needs to have as a part of the user's genre list.
    - genre_list is a list of genres that the user has provided.
    Representation Invariants:
    - self.genre_list != []
    - min_genres_game >= 0
    """
    genre_list: list[str]
    min_genres_game: int

    def __init__(self, genre_list: list[str], min_genres_game: int) -> None:
        """Initializes the game graph"""
        AbstractGameGraph.__init__(self)
        self.genre_list = genre_list
        self.min_genres_game = min_genres_game

    def add_game(self, game: Game) -> None:
        """Adds a game node into the graph if they have the minimum amount of intersecting genres with the
        user"""
        game_count = game.genre_count(self.genre_list)
        game_id = game.game_id
        if game_count >= self.min_genres_game:
            self._nodes[game_id] = GameNode(game)

    def add_edge(self, game1: GameNode, game2: GameNode) -> None:
        """Creates an edge between two game nodes if they have the minimum amount of intersecting genres
        Preconditions:
        - game1 in self._nodes and game2 in self._nodes
        """
        game1.neighbours.append(game2)
        game2.neighbours.append(game1)


def read_data_csv(csv_file: str) -> dict[int, Game]:
    """Load data from a CSV file and output the data as a mapping between game ids and their corresponding Game object.
    Preconditions:
        - csv_file refers to a valid CSV file
    """
    result = {}

    with open(csv_file) as f:
        reader = csv.reader(f)

        next(reader)  # skip headers

        for row in reader:
            game_id = int(row[0])
            name = row[1]
            date_release = row[2]
            genres = []
            operating_systems = {'win': bool(row[3]),
                                 'mac': bool(row[4]),
                                 'linux': bool(row[5])}
            # 6 is skipped for rating(all words)
            positive_ratio = int(row[7])
            # 8 is skipped for user_reviews
            price_final = float(row[9])
            # Last 3 are price_original,discount,steam_deck, they are skipped
            curr_game = Game(name, game_id, genres, date_release, operating_systems, price_final, positive_ratio, None)
            result[game_id] = curr_game
    return result


def read_metadata_json(json_file: str) -> list[tuple]:
    """Load data from a JSON file and output the data as a list of tuples. The tuple contains the game_id(index 0, int)
    and the tags(index 1, list[str]).
    Preconditions:
        - json_file refers to a valid JSON file
    """
    result = []

    with open(json_file) as f:
        for line in [str.strip(line.lower()) for line in f]:
            curr_full_metadata = json.loads(line)
            relevant_metadata = (int(curr_full_metadata.get('app_id')), curr_full_metadata.get('tags'))
            result.append(relevant_metadata)

    return result


def generate_graph(game_file: str, json_file: str, user_list: list, graph_type: str, graph_int: int) \
        -> AbstractGameGraph:
    """Creates a game graph
    Notes:
    -game_file refers to a csv file consisting of games and their attributes.
    -json_file is a json file that consists of the every game's genre in.
    -min_genre refers to the min_genre_game attribute in the game graph.
    -genre_edge refers to the min_genres_edge attribute in the game graph
    Preconditions:
    - graph_type in ['SimilarGenre', 'SimilarGame']
    """
    json_result = read_metadata_json(json_file)
    csv_result = read_data_csv(game_file)
    if graph_type == 'SimilarGenre':
        game_graph = SimilarGenreGraph(user_list, graph_int)
    else:
        game_graph = SimilarGameGraph(user_list, graph_int)

    for metadata in json_result:
        # Adds the nodes to the graph
        game = csv_result[metadata[0]]
        game.genres = metadata[1]
        game_graph.add_game(game)
    node_list = game_graph.node_list()
    # Creates edges between each node if applicable.
    for node1 in node_list:
        for node2 in node_list:
            if node1 != node2:
                game_graph.add_edge(node1, node2)
    return game_graph


def sort_games(games: list[Game]) -> None:
    """Sorts a list of games in the given list in descending order of their rating by mutating the list.
    Note:
    - This sorting function uses the iterative insert method.
    """
    for index1 in range(0, len(games) - 1):  # len(games) - 1 to prevent index out of bounds error
        if games[index1].rating < games[index1 + 1].rating:
            games[index1], games[index1 + 1] = games[index1 + 1], games[index1]
            for index2 in range(index1, 0, -1):
                if games[index2].rating > games[index2 - 1].rating:
                    games[index2], games[index2 - 1] = games[index2 - 1], games[index2]


def graph_list(user_list: list, min_int: int, graph_type: str, csv_file: str, json_file: str) \
        -> list[AbstractGameGraph]:
    """Creates a list of game graphs that vary in the amount commonly shared genres that the graph games
    have with the user.
    Preconditions:
    - min_int >= 1
    """
    game_graphs = []
    for num in range(0, min_int):
        graph = generate_graph(csv_file, json_file, user_list, graph_type, num)
        game_graphs.append(graph)
    return game_graphs


def runner(game_file: str, game_metadata_file: str) -> None:
    """Run a simulation based on the data from the given csv file."""
    # Part 1: Read datasets
    games = read_data_csv(game_file)
    games_metadata = read_metadata_json(game_metadata_file)

    for metadata in games_metadata:
        game_id, genres = metadata

        if game_id in games:
            games[game_id].genres = genres

        # Part 2: Tkinter interface(ask for preferred genres)
        # Create a new tkinter window
        root = tk.Tk()
        root.title("Genre Selector")
        root.geometry("400x300")

        # Information for user
        intro_text = tk.Label(root,
                              text="Welcome to the Steam Game Recommender!\nThis program will recommend the top 5 games "
                                   "you should play based on your preference of genre.\nPlease select the genres you're "
                                   "interested in"
                                   "below.", font=("Arial", 14))
        intro_text.grid(pady=20)

        # Call the GenreSelector class within the tkinter window
        selector = GenreSelector(root)

        # Run the tkinter mainloop
        root.mainloop()

        # Get selected genres from genre selector
        selected_genres = selector.genres

        # Part 3: Calculate meta score

        # Part 4: Give recommendations(top 5 only)