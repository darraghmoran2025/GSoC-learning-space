"""
Wolf-Sheep Predator-Prey Model
================================
A classic ecological ABM demonstrating predator-prey dynamics,
emergent population cycles (Lotka-Volterra behaviour), and the
role of resource constraints in system stability.

Three agent types:
  - GrassPatch  — background resource; regrows after being eaten
  - Sheep        — herbivore; eats grass, flees randomly, reproduces, dies of starvation
  - Wolf         — predator; eats sheep, reproduces, dies of starvation

Mesa concepts used:
  - MultiGrid (multiple agents per cell)
  - agents_by_type  (filtered AgentSet by class)
  - shuffle_do      (randomised activation)
  - agent.remove() + grid.remove_agent() (explicit two-step removal)
  - DataCollector   (multi-series population tracking)
"""

import mesa
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector


# ---------------------------------------------------------------------------
# Agent classes
# ---------------------------------------------------------------------------

class GrassPatch(mesa.Agent):
    """
    Represents a single grid cell's grass state.

    Attributes:
        fully_grown (bool): whether the patch currently has grass
        countdown (int): steps until the patch regrows (0 when fully grown)
    """

    def __init__(self, model, fully_grown: bool, countdown: int):
        super().__init__(model)
        self.fully_grown = fully_grown
        self.countdown = countdown

    def step(self):
        if not self.fully_grown:
            self.countdown -= 1
            if self.countdown <= 0:
                self.fully_grown = True
                self.countdown = self.model.grass_regrowth_time


class Sheep(mesa.Agent):
    """
    Herbivore agent. Moves randomly, eats grass, reproduces, dies of starvation.

    Attributes:
        energy (float): current energy reserve; decremented each step
    """

    def __init__(self, model, energy: float):
        super().__init__(model)
        self.energy = energy

    def step(self):
        self._move()
        self.energy -= 1

        self._eat_grass()

        if self.energy <= 0:
            self._die()
            return

        self._reproduce()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _move(self):
        # get_neighborhood returns positions; get_neighbors returns agents
        # PAIN POINT: easy to mix these two up — see README
        possible_moves = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        new_pos = self.random.choice(possible_moves)
        self.model.grid.move_agent(self, new_pos)

    def _eat_grass(self):
        # get_cell_list_contents returns ALL agents at the given cells —
        # must filter by type explicitly
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        patches = [obj for obj in cell_contents if isinstance(obj, GrassPatch)]
        if patches and patches[0].fully_grown:
            self.energy += self.model.sheep_gain_from_food
            patches[0].fully_grown = False
            patches[0].countdown = self.model.grass_regrowth_time

    def _reproduce(self):
        if self.random.random() < self.model.sheep_reproduce:
            self.energy /= 2
            lamb = Sheep(self.model, self.energy)
            self.model.grid.place_agent(lamb, self.pos)

    def _die(self):
        # PAIN POINT: two-step removal required in Mesa 3.x
        # grid.remove_agent() removes from the spatial grid
        # agent.remove() removes from model.agents / AgentSet
        # Calling only one leaves a ghost in the other structure
        self.model.grid.remove_agent(self)
        self.remove()


class Wolf(mesa.Agent):
    """
    Predator agent. Moves randomly, eats sheep, reproduces, dies of starvation.

    Attributes:
        energy (float): current energy reserve; decremented each step
    """

    def __init__(self, model, energy: float):
        super().__init__(model)
        self.energy = energy

    def step(self):
        self._move()
        self.energy -= 1

        self._eat_sheep()

        if self.energy <= 0:
            self._die()
            return

        self._reproduce()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _move(self):
        possible_moves = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        new_pos = self.random.choice(possible_moves)
        self.model.grid.move_agent(self, new_pos)

    def _eat_sheep(self):
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        sheep_here = [obj for obj in cell_contents if isinstance(obj, Sheep)]
        if sheep_here:
            prey = self.random.choice(sheep_here)
            self.energy += self.model.wolf_gain_from_food
            # Remove the eaten sheep from both grid and model
            self.model.grid.remove_agent(prey)
            prey.remove()

    def _reproduce(self):
        if self.random.random() < self.model.wolf_reproduce:
            self.energy /= 2
            pup = Wolf(self.model, self.energy)
            self.model.grid.place_agent(pup, self.pos)

    def _die(self):
        self.model.grid.remove_agent(self)
        self.remove()


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class WolfSheepModel(mesa.Model):
    """
    Wolf-Sheep Predator-Prey Model.

    Parameters:
        width, height (int): grid dimensions
        initial_sheep (int): starting sheep count
        initial_wolves (int): starting wolf count
        sheep_reproduce (float): per-step reproduction probability for sheep
        wolf_reproduce (float): per-step reproduction probability for wolves
        wolf_gain_from_food (int): energy gained by wolf per sheep eaten
        sheep_gain_from_food (int): energy gained by sheep per grass patch eaten
        grass_regrowth_time (int): steps until an eaten patch regrows
        seed (int | None): random seed
    """

    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        initial_sheep: int = 100,
        initial_wolves: int = 25,
        sheep_reproduce: float = 0.04,
        wolf_reproduce: float = 0.05,
        wolf_gain_from_food: int = 20,
        sheep_gain_from_food: int = 4,
        grass_regrowth_time: int = 30,
        seed=None,
    ):
        super().__init__(seed=seed)

        self.width = width
        self.height = height
        self.initial_sheep = initial_sheep
        self.initial_wolves = initial_wolves
        self.sheep_reproduce = sheep_reproduce
        self.wolf_reproduce = wolf_reproduce
        self.wolf_gain_from_food = wolf_gain_from_food
        self.sheep_gain_from_food = sheep_gain_from_food
        self.grass_regrowth_time = grass_regrowth_time

        self.grid = MultiGrid(width, height, torus=True)

        self.datacollector = DataCollector(
            model_reporters={
                "wolves": lambda m: len(m.agents_by_type[Wolf]),
                "sheep": lambda m: len(m.agents_by_type[Sheep]),
                "grass_patches": lambda m: sum(
                    1 for a in m.agents_by_type[GrassPatch] if a.fully_grown
                ),
            }
        )

        # ----------------------------------------------------------------
        # Populate grid
        # ----------------------------------------------------------------

        # One GrassPatch per cell — randomly assign grown/ungrown
        for _, pos in self.grid.coord_iter():
            fully_grown = self.random.random() < 0.5
            countdown = (
                0
                if fully_grown
                else self.random.randrange(1, grass_regrowth_time + 1)
            )
            patch = GrassPatch(self, fully_grown, countdown)
            self.grid.place_agent(patch, pos)

        # Sheep — random positions, random initial energy
        for _ in range(initial_sheep):
            pos = (
                self.random.randrange(width),
                self.random.randrange(height),
            )
            energy = self.random.randrange(2 * sheep_gain_from_food)
            sheep = Sheep(self, float(energy))
            self.grid.place_agent(sheep, pos)

        # Wolves — random positions, random initial energy
        for _ in range(initial_wolves):
            pos = (
                self.random.randrange(width),
                self.random.randrange(height),
            )
            energy = self.random.randrange(2 * wolf_gain_from_food)
            wolf = Wolf(self, float(energy))
            self.grid.place_agent(wolf, pos)

        self.running = True
        self.datacollector.collect(self)

    # ----------------------------------------------------------------
    # Step logic — ORDER MATTERS
    # Grass grows first → sheep eat and reproduce → wolves eat and reproduce
    # Changing this order measurably shifts equilibrium population sizes.
    # ----------------------------------------------------------------

    def step(self):
        self.agents_by_type[GrassPatch].do("step")           # deterministic regrowth
        self.agents_by_type[Sheep].shuffle_do("step")        # random activation order
        self.agents_by_type[Wolf].shuffle_do("step")         # random activation order

        self.datacollector.collect(self)

        # Halt if either animal population goes extinct
        if (
            len(self.agents_by_type[Wolf]) == 0
            or len(self.agents_by_type[Sheep]) == 0
        ):
            self.running = False
