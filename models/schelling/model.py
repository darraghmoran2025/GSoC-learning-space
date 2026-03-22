"""
Schelling Segregation Model
============================
Classic model from Thomas Schelling (1971) demonstrating how mild individual
preferences for similar neighbours produce dramatic macro-level segregation.

Reference: Schelling, T.C. (1971). Dynamic models of segregation.
           Journal of Mathematical Sociology, 1(2), 143-186.
"""

import mesa
from mesa.space import SingleGrid
from mesa.datacollection import DataCollector


class SchellingAgent(mesa.Agent):
    """
    A resident agent on the grid.

    Attributes:
        agent_type (int): 0 = minority group, 1 = majority group
        homophily (int): minimum number of same-type neighbours required to be happy
        happy (bool): whether the agent's homophily threshold is currently met
    """

    def __init__(self, model, agent_type: int, homophily: int):
        super().__init__(model)
        self.agent_type = agent_type
        self.homophily = homophily
        self.happy = False

    def step(self):
        neighbours = self.model.grid.get_neighbors(self.pos, moore=True)
        similar = sum(1 for n in neighbours if n.agent_type == self.agent_type)
        self.happy = similar >= self.homophily

        if not self.happy:
            self.model.grid.move_to_empty(self)


class SchellingModel(mesa.Model):
    """
    Schelling Segregation Model.

    Parameters:
        width (int): grid width
        height (int): grid height
        density (float): probability that any given cell is occupied
        minority_pc (float): fraction of agents that are minority type (0)
        homophily (int): minimum same-type neighbours for an agent to be happy
        seed (int | None): random seed for reproducibility
    """

    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        density: float = 0.8,
        minority_pc: float = 0.2,
        homophily: int = 3,
        seed=None,
    ):
        super().__init__(seed=seed)

        self.width = width
        self.height = height
        self.density = density
        self.minority_pc = minority_pc
        self.homophily = homophily

        self.grid = SingleGrid(width, height, torus=True)

        self.datacollector = DataCollector(
            model_reporters={
                "happy_count": lambda m: sum(1 for a in m.agents if a.happy),
                "pct_happy": lambda m: (
                    sum(1 for a in m.agents if a.happy) / len(list(m.agents)) * 100
                    if len(list(m.agents)) > 0
                    else 0
                ),
                "n_agents": lambda m: len(list(m.agents)),
            }
        )

        # Populate grid
        for _, pos in self.grid.coord_iter():
            if self.random.random() < self.density:
                agent_type = 0 if self.random.random() < self.minority_pc else 1
                agent = SchellingAgent(self, agent_type, self.homophily)
                self.grid.place_agent(agent, pos)

        self.running = True
        self.datacollector.collect(self)

    def step(self):
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)

        # Stop when everyone is happy
        if all(a.happy for a in self.agents):
            self.running = False
