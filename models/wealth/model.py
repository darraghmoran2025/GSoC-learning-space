"""
Wealth Distribution Model (Extended)
======================================
Extends the classic Boltzmann Wealth / MoneyModel with:
  - Network topology (scale-free, random, small-world) instead of a flat grid
  - Three behavioural agent types: Saver, Spender, Balanced
  - Agent-level data collection (wealth snapshots per agent per step)
  - Gini coefficient + Lorenz curve data tracked over time
  - Network centrality as a predictor of wealth accumulation

The core mechanism is unchanged from the tutorial MoneyModel: agents
with wealth > 0 transfer one unit to a random neighbour each step.
All the interesting variance comes from network structure and agent type.

Mesa concepts used:
  - NetworkGrid  (agents on a NetworkX graph)
  - DataCollector with both model_reporters AND agent_reporters
  - AgentSet filtering
  - Custom model-level computed statistics
"""

import mesa
import networkx as nx
from mesa.space import NetworkGrid
from mesa.datacollection import DataCollector


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def gini_coefficient(wealth_values: list[float]) -> float:
    """
    Compute the Gini coefficient for a list of wealth values.
    0 = perfect equality, 1 = total inequality.
    """
    n = len(wealth_values)
    if n == 0 or sum(wealth_values) == 0:
        return 0.0
    w = sorted(wealth_values)
    total = sum(w)
    weighted_sum = sum((2 * (i + 1) - n - 1) * w[i] for i in range(n))
    return weighted_sum / (n * total)


def lorenz_points(wealth_values: list[float]) -> tuple[list, list]:
    """
    Compute Lorenz curve (x, y) points.
    x = cumulative share of population (poorest to richest)
    y = cumulative share of wealth
    Returns two lists suitable for matplotlib plotting.
    """
    w = sorted(wealth_values)
    n = len(w)
    total = sum(w) or 1
    cum_pop = [0.0] + [(i + 1) / n for i in range(n)]
    cum_wealth = [0.0]
    running = 0
    for v in w:
        running += v
        cum_wealth.append(running / total)
    return cum_pop, cum_wealth


# ---------------------------------------------------------------------------
# Agent types
# ---------------------------------------------------------------------------

class WealthAgent(mesa.Agent):
    """
    An agent on the wealth network.

    agent_type controls transfer behaviour:
      "balanced" — always gives 1 unit to a random neighbour (baseline MoneyModel)
      "saver"    — only gives if wealth > save_threshold; probability-gated
      "spender"  — gives extra_give units per step when possible
    """

    def __init__(self, model, agent_type: str = "balanced",
                 save_threshold: int = 3, extra_give: int = 1):
        super().__init__(model)
        self.wealth = 1
        self.agent_type = agent_type
        self.save_threshold = save_threshold
        self.extra_give = extra_give   # used by spender

    def step(self):
        if self.wealth <= 0:
            return

        neighbours = self.model.grid.get_neighbors(self.pos, include_center=False)
        if not neighbours:
            return

        recipient = self.random.choice(neighbours)

        if self.agent_type == "saver":
            # Only give when above threshold, and only with 50% probability
            if self.wealth > self.save_threshold and self.random.random() < 0.5:
                self.wealth -= 1
                recipient.wealth += 1

        elif self.agent_type == "spender":
            # Give extra_give units per step (if available)
            give = min(self.extra_give, self.wealth)
            self.wealth -= give
            recipient.wealth += give

        else:  # "balanced" — baseline behaviour
            self.wealth -= 1
            recipient.wealth += 1


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

NETWORK_TYPES = {
    "barabasi_albert": "Scale-free (Barabási–Albert) — realistic social network, rich-get-richer",
    "erdos_renyi":     "Random (Erdős–Rényi) — uniform degree distribution, theoretical baseline",
    "watts_strogatz":  "Small-world (Watts–Strogatz) — high clustering + short path lengths",
    "complete":        "Complete graph — every agent connected to every other (mean-field limit)",
}


class WealthModel(mesa.Model):
    """
    Extended Wealth Distribution Model on a network.

    Parameters:
        n_agents (int): total number of agents
        network_type (str): one of 'barabasi_albert', 'erdos_renyi',
                            'watts_strogatz', 'complete'
        pct_savers (float): fraction of agents that are savers   [0, 1]
        pct_spenders (float): fraction of agents that are spenders [0, 1]
        initial_wealth (int): starting wealth per agent
        seed (int | None): random seed
    """

    def __init__(
        self,
        n_agents: int = 100,
        network_type: str = "barabasi_albert",
        pct_savers: float = 0.0,
        pct_spenders: float = 0.0,
        initial_wealth: int = 1,
        seed=None,
    ):
        super().__init__(seed=seed)

        self.n_agents = n_agents
        self.network_type = network_type
        self.initial_wealth = initial_wealth

        # ----------------------------------------------------------------
        # Build network
        # ----------------------------------------------------------------
        G = self._build_network(network_type, n_agents, seed)
        self.G = G
        self.grid = NetworkGrid(G)

        # Pre-compute degree centrality for analysis
        self.degree_centrality = nx.degree_centrality(G)

        # ----------------------------------------------------------------
        # Data collection — model AND agent level
        # ----------------------------------------------------------------
        self.datacollector = DataCollector(
            model_reporters={
                "gini": lambda m: gini_coefficient(
                    [a.wealth for a in m.agents]
                ),
                "mean_wealth": lambda m: (
                    sum(a.wealth for a in m.agents) / max(1, len(list(m.agents)))
                ),
                "max_wealth": lambda m: max((a.wealth for a in m.agents), default=0),
                "min_wealth": lambda m: min((a.wealth for a in m.agents), default=0),
                "n_zero_wealth": lambda m: sum(1 for a in m.agents if a.wealth == 0),
                "total_wealth": lambda m: sum(a.wealth for a in m.agents),
            },
            # Agent-level reporters: snapshotted every step
            # Enables post-hoc wealth trajectory per agent
            agent_reporters={
                "wealth": "wealth",
                "agent_type": "agent_type",
            },
        )

        # ----------------------------------------------------------------
        # Populate network
        # ----------------------------------------------------------------
        n_savers = int(n_agents * pct_savers)
        n_spenders = int(n_agents * pct_spenders)
        n_balanced = n_agents - n_savers - n_spenders

        types = (
            ["saver"] * n_savers
            + ["spender"] * n_spenders
            + ["balanced"] * n_balanced
        )
        self.random.shuffle(types)

        for node_id, agent_type in zip(sorted(G.nodes()), types):
            agent = WealthAgent(self, agent_type=agent_type)
            agent.wealth = initial_wealth
            self.grid.place_agent(agent, node_id)

        self.running = True
        self.datacollector.collect(self)

    # ----------------------------------------------------------------
    # Network builder
    # ----------------------------------------------------------------

    def _build_network(self, network_type: str, n: int, seed) -> nx.Graph:
        if network_type == "barabasi_albert":
            return nx.barabasi_albert_graph(n, m=2, seed=seed)
        elif network_type == "erdos_renyi":
            return nx.erdos_renyi_graph(n, p=0.05, seed=seed)
        elif network_type == "watts_strogatz":
            return nx.watts_strogatz_graph(n, k=4, p=0.1, seed=seed)
        elif network_type == "complete":
            return nx.complete_graph(n)
        else:
            raise ValueError(
                f"Unknown network_type '{network_type}'. "
                f"Choose from: {list(NETWORK_TYPES.keys())}"
            )

    # ----------------------------------------------------------------
    # Step
    # ----------------------------------------------------------------

    def step(self):
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)

    # ----------------------------------------------------------------
    # Analysis helpers (called from run.py)
    # ----------------------------------------------------------------

    def wealth_by_centrality(self) -> list[tuple[float, float]]:
        """Return [(degree_centrality, wealth)] for all agents."""
        return [
            (self.degree_centrality[agent.pos], agent.wealth)
            for agent in self.agents
        ]

    def wealth_by_type(self) -> dict[str, list[int]]:
        """Return {type: [wealth, ...]} for post-hoc analysis."""
        result: dict[str, list] = {}
        for agent in self.agents:
            result.setdefault(agent.agent_type, []).append(agent.wealth)
        return result
