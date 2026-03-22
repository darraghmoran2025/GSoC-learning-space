"""
BDI Foraging Model
====================
A concrete application of the BDI architecture (see bdi_base.py) to a
resource-foraging scenario on a grid.

Scenario:
  - A grid world contains scattered FoodPatches that slowly regrow
  - ForagerAgents start near a shared home base
  - Each forager has partial vision: it only knows about food it has seen
  - Agents must balance foraging, returning home to deposit food, and conserving energy

This model is designed to make the BDI deliberation cycle visible and
inspectable — agent desires, replanning counts, and intention queue length
are all tracked in the DataCollector.

Mesa concepts used:
  - SingleGrid (one agent per cell — collision forces replanning, demonstrating BDI recovery)
  - agents_by_type filtering
  - DataCollector with agent_reporters capturing BDI internals
  - agent.remove() + grid.remove_agent() for food consumption and forager death
"""

import mesa
from mesa.space import SingleGrid
from mesa.datacollection import DataCollector
from collections import deque
from enum import Enum, auto

from bdi_base import BDIAgent


# ---------------------------------------------------------------------------
# Desires
# ---------------------------------------------------------------------------

class ForagerDesire(Enum):
    REST        = auto()   # energy critically low — wait to recover
    RETURN_HOME = auto()   # carrying food — go deposit it
    FORAGE      = auto()   # know food locations — go collect
    EXPLORE     = auto()   # no known food — random walk to discover


# ---------------------------------------------------------------------------
# Environment agent: food patch
# ---------------------------------------------------------------------------

class FoodPatch(mesa.Agent):
    """Passive food item. Consumed by ForagerAgents on collection."""

    def step(self):
        pass  # static; regrowth is handled by the model


# ---------------------------------------------------------------------------
# BDI ForagerAgent
# ---------------------------------------------------------------------------

class ForagerAgent(BDIAgent, mesa.Agent):
    """
    BDI agent that forages for food and deposits it at a home base.

    Beliefs tracked:
        energy          — current energy level
        carrying_food   — bool: holding food to deposit
        known_food      — set of grid positions where food was last seen
        home            — home base position

    Desires (priority order):
        REST > RETURN_HOME > FORAGE > EXPLORE

    Intentions: sequences of ("ACTION", {args}) tuples executed one per step.
    """

    def __init__(self, model, home_pos: tuple, vision_range: int = 3,
                 start_energy: int = 20, max_energy: int = 30):
        mesa.Agent.__init__(self, model)
        BDIAgent.__init__(self)

        self.home_pos     = home_pos
        self.vision_range = vision_range
        self.energy       = start_energy
        self.max_energy   = max_energy
        self.food_collected = 0

        # Seed initial beliefs
        self.beliefs["energy"]         = start_energy
        self.beliefs["carrying_food"]  = False
        self.beliefs["known_food"]     = set()
        self.beliefs["home"]           = home_pos

    # ------------------------------------------------------------------
    # BDI interface
    # ------------------------------------------------------------------

    def perceive(self):
        """Scan cells within vision_range and update food belief map."""
        self.beliefs["energy"]        = self.energy
        self.beliefs["carrying_food"] = self.beliefs["carrying_food"]

        visible = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=True, radius=self.vision_range
        )
        for pos in visible:
            has_food = any(
                isinstance(a, FoodPatch)
                for a in self.model.grid.get_cell_list_contents([pos])
            )
            if has_food:
                self.beliefs["known_food"].add(pos)
            else:
                # Remove stale belief — food was eaten or never there
                self.beliefs["known_food"].discard(pos)

    def get_desires(self) -> list:
        desires = []
        if self.beliefs["energy"] <= 5:
            desires.append(ForagerDesire.REST)
        if self.beliefs["carrying_food"]:
            desires.append(ForagerDesire.RETURN_HOME)
        if not self.beliefs["carrying_food"] and self.beliefs["known_food"]:
            desires.append(ForagerDesire.FORAGE)
        if not self.beliefs["carrying_food"] and not self.beliefs["known_food"]:
            desires.append(ForagerDesire.EXPLORE)
        return desires

    def plan(self, desire) -> deque:
        """
        Generate an intention sequence for the given desire.

        Plans are greedy paths (one MOVE per cell) followed by a
        terminal action (COLLECT / DEPOSIT / WAIT).
        If a MOVE action fails mid-plan (cell blocked), the agent
        replans automatically via BDIAgent._execute().
        """
        q = deque()

        if desire == ForagerDesire.REST:
            q.append(("WAIT", {}))

        elif desire == ForagerDesire.RETURN_HOME:
            for pos in self._greedy_path(self.beliefs["home"]):
                q.append(("MOVE", {"target": pos}))
            q.append(("DEPOSIT", {}))

        elif desire == ForagerDesire.FORAGE:
            nearest = min(
                self.beliefs["known_food"],
                key=lambda p: self._manhattan(self.pos, p)
            )
            for pos in self._greedy_path(nearest):
                q.append(("MOVE", {"target": pos}))
            q.append(("COLLECT", {"expected_pos": nearest}))

        elif desire == ForagerDesire.EXPLORE:
            # Random walk of up to 6 steps
            cur = self.pos
            for _ in range(6):
                candidates = self.model.grid.get_neighborhood(
                    cur, moore=True, include_center=False
                )
                free = [p for p in candidates
                        if not any(isinstance(a, ForagerAgent)
                                   for a in self.model.grid.get_cell_list_contents([p]))]
                if free:
                    nxt = self.random.choice(free)
                    q.append(("MOVE", {"target": nxt}))
                    cur = nxt

        return q

    def execute_action(self, action: str, args: dict) -> bool:
        if action == "WAIT":
            self.energy = min(self.max_energy, self.energy + 2)
            return True

        elif action == "MOVE":
            target = args["target"]
            # Fail if another forager has moved here since we planned
            occupants = self.model.grid.get_cell_list_contents([target])
            if any(isinstance(a, ForagerAgent) for a in occupants):
                return False  # triggers replan
            self.model.grid.move_agent(self, target)
            self.energy -= 1
            if self.energy <= 0:
                self._die()
            return True

        elif action == "COLLECT":
            contents = self.model.grid.get_cell_list_contents([self.pos])
            food_here = [a for a in contents if isinstance(a, FoodPatch)]
            if food_here:
                self.model.grid.remove_agent(food_here[0])
                food_here[0].remove()
                self.beliefs["carrying_food"] = True
                self.beliefs["known_food"].discard(self.pos)
                return True
            else:
                # Food already eaten — stale belief, replan
                self.beliefs["known_food"].discard(args.get("expected_pos", self.pos))
                return False

        elif action == "DEPOSIT":
            if self.pos == self.beliefs["home"] and self.beliefs["carrying_food"]:
                self.beliefs["carrying_food"] = False
                self.food_collected += 1
                self.energy = min(self.max_energy, self.energy + 10)
                return True
            return False  # not home yet, replan

        return False

    def step(self):
        self.bdi_step()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _die(self):
        self.model.grid.remove_agent(self)
        self.remove()

    def _manhattan(self, a: tuple, b: tuple) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _greedy_path(self, target: tuple) -> list[tuple]:
        """
        Build a greedy path toward target using Manhattan distance.
        Generates at most width+height steps.
        Skips occupied cells where possible; accepts them as fallback
        (MOVE will then fail and trigger replanning — intentional).
        """
        path = []
        pos = self.pos
        max_steps = self.model.width + self.model.height

        for _ in range(max_steps):
            if pos == target:
                break
            candidates = sorted(
                self.model.grid.get_neighborhood(pos, moore=True, include_center=False),
                key=lambda p: self._manhattan(p, target)
            )
            free = [p for p in candidates
                    if not any(isinstance(a, ForagerAgent)
                               for a in self.model.grid.get_cell_list_contents([p]))]
            nxt = free[0] if free else candidates[0]
            path.append(nxt)
            pos = nxt

        return path


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class ForagingModel(mesa.Model):
    """
    BDI Foraging Model.

    Parameters:
        width, height (int): grid dimensions
        n_foragers (int): number of BDI forager agents
        n_food (int): initial food items placed on grid
        food_regrow_rate (float): probability per empty cell per step of food regrowing
        vision_range (int): how far foragers can see (Moore neighbourhood radius)
        seed: random seed
    """

    def __init__(
        self,
        width: int = 25,
        height: int = 25,
        n_foragers: int = 10,
        n_food: int = 60,
        food_regrow_rate: float = 0.005,
        vision_range: int = 3,
        seed=None,
    ):
        super().__init__(seed=seed)

        self.width            = width
        self.height           = height
        self.food_regrow_rate = food_regrow_rate
        self.home_pos         = (width // 2, height // 2)

        self.grid = SingleGrid(width, height, torus=False)

        self.datacollector = DataCollector(
            model_reporters={
                "foragers_alive": lambda m: len(list(m.agents_by_type[ForagerAgent])),
                "food_on_grid":   lambda m: len(list(m.agents_by_type[FoodPatch])),
                "total_collected": lambda m: sum(
                    a.food_collected for a in m.agents_by_type[ForagerAgent]
                ),
                "avg_energy": lambda m: (
                    sum(a.energy for a in m.agents_by_type[ForagerAgent])
                    / max(1, len(list(m.agents_by_type[ForagerAgent])))
                ),
                "avg_replans": lambda m: (
                    sum(a.bdi_stats["replans"] for a in m.agents_by_type[ForagerAgent])
                    / max(1, len(list(m.agents_by_type[ForagerAgent])))
                ),
                "avg_failed_actions": lambda m: (
                    sum(a.bdi_stats["failed_actions"] for a in m.agents_by_type[ForagerAgent])
                    / max(1, len(list(m.agents_by_type[ForagerAgent])))
                ),
            },
            agent_reporters={
                "energy":         lambda a: a.energy if isinstance(a, ForagerAgent) else None,
                "food_collected": lambda a: a.food_collected if isinstance(a, ForagerAgent) else None,
                "replans":        lambda a: a.bdi_stats["replans"] if isinstance(a, ForagerAgent) else None,
                "desire":         lambda a: (
                    a.current_desire.name
                    if isinstance(a, ForagerAgent) and a.current_desire else None
                ),
                "carrying_food":  lambda a: (
                    a.beliefs.get("carrying_food")
                    if isinstance(a, ForagerAgent) else None
                ),
            },
        )

        # Place food — avoid home base area
        all_coords = [(x, y) for x in range(width) for y in range(height)]
        non_home = [
            p for p in all_coords
            if self._manhattan(p, self.home_pos) > 3
        ]
        food_cells = self.random.sample(non_home, min(n_food, len(non_home)))
        for pos in food_cells:
            self.grid.place_agent(FoodPatch(self), pos)

        # Place foragers near home base
        home_area = [
            p for p in self.grid.get_neighborhood(
                self.home_pos, moore=True, include_center=True, radius=2
            )
            if self.grid.is_cell_empty(p)
        ]
        self.random.shuffle(home_area)
        for i in range(min(n_foragers, len(home_area))):
            agent = ForagerAgent(
                self, self.home_pos, vision_range=vision_range
            )
            self.grid.place_agent(agent, home_area[i])

        self.running = True
        self.datacollector.collect(self)

    def step(self):
        # Regrow food on random empty cells
        for x in range(self.width):
            for y in range(self.height):
                if self.grid.is_cell_empty((x, y)):
                    if self.random.random() < self.food_regrow_rate:
                        self.grid.place_agent(FoodPatch(self), (x, y))

        self.agents_by_type[ForagerAgent].shuffle_do("step")
        self.datacollector.collect(self)

        if not list(self.agents_by_type[ForagerAgent]):
            self.running = False

    def _manhattan(self, a: tuple, b: tuple) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
