"""
Reinforcement Learning Agent — Q-Learning on a Grid
======================================================
Demonstrates the third pillar of the Mesa Behavioral Framework: learning agents.

A Q-learning agent navigates a grid to collect rewards (food patches) while
avoiding penalties (hazard cells). It learns a policy purely from experience —
no hardcoded rules, no map, no BDI plan.

Compare with:
  - Wolf-Sheep: purely reactive (energy bookkeeping, no learning)
  - BDI Forager: deliberative but rule-based (no adaptation)
  - RL Agent: adapts its behaviour based on reward history

Q-Learning recap:
  Q(s, a) ← Q(s, a) + α · [r + γ · max_a' Q(s', a') − Q(s, a)]
  where:
    s  = current state (agent position)
    a  = action taken (move direction)
    r  = reward received
    s' = resulting state
    α  = learning rate
    γ  = discount factor

Mesa concepts used:
  - SingleGrid
  - DataCollector with agent_reporters (Q-table size, epsilon, cumulative reward)
  - Multiple agent types on the same grid (QLearner + RewardPatch + HazardPatch)
  - Comparison run: reactive baseline agent vs. Q-learning agent
"""

import mesa
from mesa.space import SingleGrid
from mesa.datacollection import DataCollector
import numpy as np
from collections import defaultdict


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

ACTIONS = ["UP", "DOWN", "LEFT", "RIGHT"]
ACTION_DELTAS = {
    "UP":    (0,  1),
    "DOWN":  (0, -1),
    "LEFT":  (-1, 0),
    "RIGHT": ( 1, 0),
}

# ---------------------------------------------------------------------------
# Environment patches
# ---------------------------------------------------------------------------

class RewardPatch(mesa.Agent):
    """A food/reward cell. Consumed on contact, respawns after cooldown."""

    def __init__(self, model, reward: float = 1.0, respawn_time: int = 10):
        super().__init__(model)
        self.reward = reward
        self.respawn_time = respawn_time
        self.active = True
        self._cooldown = 0

    def step(self):
        if not self.active:
            self._cooldown -= 1
            if self._cooldown <= 0:
                self.active = True

    def consume(self) -> float:
        """Collect the reward and deactivate until respawn."""
        if self.active:
            self.active = False
            self._cooldown = self.respawn_time
            return self.reward
        return 0.0


class HazardPatch(mesa.Agent):
    """A penalty cell. Permanent — does not deactivate."""

    def __init__(self, model, penalty: float = -0.5):
        super().__init__(model)
        self.penalty = penalty

    def step(self):
        pass


# ---------------------------------------------------------------------------
# Reactive baseline agent (no learning — random walk that avoids hazards)
# ---------------------------------------------------------------------------

class ReactiveAgent(mesa.Agent):
    """
    Simple reactive baseline: moves randomly, avoids cells it remembers
    as hazardous. No learning — just a hard-coded avoidance rule.
    Used to benchmark Q-learning improvement.
    """

    def __init__(self, model):
        super().__init__(model)
        self.cumulative_reward = 0.0
        self._known_hazards: set = set()

    def step(self):
        neighbours = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=False
        )
        safe = [p for p in neighbours if p not in self._known_hazards
                and self.model.grid.is_cell_empty(p) or
                not any(isinstance(a, HazardPatch)
                        for a in self.model.grid.get_cell_list_contents([p]))]
        target = self.random.choice(safe if safe else neighbours)
        self.model.grid.move_agent(self, target)
        self.cumulative_reward += self._collect_reward()

    def _collect_reward(self) -> float:
        total = 0.0
        for agent in self.model.grid.get_cell_list_contents([self.pos]):
            if isinstance(agent, RewardPatch):
                total += agent.consume()
            elif isinstance(agent, HazardPatch):
                total += agent.penalty
                self._known_hazards.add(self.pos)
        return total


# ---------------------------------------------------------------------------
# Q-Learning agent
# ---------------------------------------------------------------------------

class QLearnerAgent(mesa.Agent):
    """
    Tabular Q-learning agent navigating a grid environment.

    State space:   (x, y) grid position  [width × height states]
    Action space:  {UP, DOWN, LEFT, RIGHT}
    Reward signal: +reward for RewardPatch, -penalty for HazardPatch, -0.01/step

    Exploration: ε-greedy with exponential decay
      ε decays from epsilon_start → epsilon_min over the simulation
    """

    def __init__(
        self,
        model,
        alpha: float = 0.1,       # learning rate
        gamma: float = 0.95,      # discount factor
        epsilon_start: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
    ):
        super().__init__(model)
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        # Q-table: state → {action → Q-value}
        # defaultdict avoids KeyError on unseen states
        self.q_table: dict[tuple, dict[str, float]] = defaultdict(
            lambda: {a: 0.0 for a in ACTIONS}
        )

        # Diagnostics
        self.cumulative_reward = 0.0
        self.steps_taken = 0
        self._last_state = None
        self._last_action = None

    # ------------------------------------------------------------------
    # Core Q-learning logic
    # ------------------------------------------------------------------

    def _choose_action(self, state: tuple) -> str:
        """ε-greedy action selection."""
        if self.random.random() < self.epsilon:
            return self.random.choice(ACTIONS)
        q_vals = self.q_table[state]
        return max(q_vals, key=q_vals.get)

    def _target_pos(self, action: str) -> tuple:
        """Compute target grid position for an action (clamped to grid bounds)."""
        dx, dy = ACTION_DELTAS[action]
        x, y = self.pos
        nx = max(0, min(self.model.grid.width - 1, x + dx))
        ny = max(0, min(self.model.grid.height - 1, y + dy))
        return (nx, ny)

    def _collect_reward(self) -> float:
        """Collect reward/penalty from current cell. Returns scalar reward."""
        total = -0.01  # small step penalty encourages efficiency
        for agent in self.model.grid.get_cell_list_contents([self.pos]):
            if isinstance(agent, RewardPatch):
                total += agent.consume()
            elif isinstance(agent, HazardPatch):
                total += agent.penalty
        return total

    def _update_q(self, state, action, reward, next_state):
        """Apply Q-learning update rule."""
        old_q = self.q_table[state][action]
        next_max = max(self.q_table[next_state].values())
        new_q = old_q + self.alpha * (reward + self.gamma * next_max - old_q)
        self.q_table[state][action] = new_q

    # ------------------------------------------------------------------
    # Mesa step
    # ------------------------------------------------------------------

    def step(self):
        state = self.pos
        action = self._choose_action(state)
        target = self._target_pos(action)

        # Move (stays in place if target occupied by another learner)
        cell_contents = self.model.grid.get_cell_list_contents([target])
        blocking = [a for a in cell_contents
                    if isinstance(a, (QLearnerAgent, ReactiveAgent))]
        if not blocking:
            self.model.grid.move_agent(self, target)

        reward = self._collect_reward()
        next_state = self.pos

        self._update_q(state, action, reward, next_state)

        # Decay exploration rate
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        self.cumulative_reward += reward
        self.steps_taken += 1

    @property
    def q_table_size(self) -> int:
        """Number of state-action pairs with non-zero Q-values."""
        return sum(
            1 for qs in self.q_table.values()
            for v in qs.values() if v != 0.0
        )


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class RLGridModel(mesa.Model):
    """
    Grid environment with Q-learning and reactive agents competing for rewards.

    Parameters:
        width, height       : grid dimensions
        n_learners          : number of Q-learning agents
        n_reactive          : number of reactive baseline agents
        n_rewards           : number of RewardPatch cells
        n_hazards           : number of HazardPatch cells
        reward_value        : reward per collection
        hazard_penalty      : penalty per hazard step
        alpha, gamma        : Q-learning hyperparameters
        epsilon_start/min/decay : exploration schedule
        seed                : random seed
    """

    def __init__(
        self,
        width: int = 15,
        height: int = 15,
        n_learners: int = 1,
        n_reactive: int = 1,
        n_rewards: int = 20,
        n_hazards: int = 10,
        reward_value: float = 1.0,
        hazard_penalty: float = -0.5,
        alpha: float = 0.1,
        gamma: float = 0.95,
        epsilon_start: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        seed=None,
    ):
        super().__init__(seed=seed)

        self.width = width
        self.height = height
        self.grid = SingleGrid(width, height, torus=False)

        # ----------------------------------------------------------------
        # Data collection
        # ----------------------------------------------------------------
        self.datacollector = DataCollector(
            model_reporters={
                "learner_reward": lambda m: sum(
                    a.cumulative_reward for a in m.agents
                    if isinstance(a, QLearnerAgent)
                ),
                "reactive_reward": lambda m: sum(
                    a.cumulative_reward for a in m.agents
                    if isinstance(a, ReactiveAgent)
                ),
                "active_rewards": lambda m: sum(
                    1 for a in m.agents
                    if isinstance(a, RewardPatch) and a.active
                ),
            },
            agent_reporters={
                "cumulative_reward": lambda a: getattr(a, "cumulative_reward", None),
                "epsilon": lambda a: getattr(a, "epsilon", None),
                "q_table_size": lambda a: getattr(a, "q_table_size", None),
            },
        )

        # ----------------------------------------------------------------
        # Place environment patches first (non-moving)
        # ----------------------------------------------------------------
        all_cells = [(x, y) for x in range(width) for y in range(height)]
        self.random.shuffle(all_cells)
        cell_iter = iter(all_cells)

        for _ in range(n_rewards):
            pos = next(cell_iter)
            patch = RewardPatch(self, reward=reward_value)
            self.grid.place_agent(patch, pos)

        for _ in range(n_hazards):
            pos = next(cell_iter)
            hazard = HazardPatch(self, penalty=hazard_penalty)
            self.grid.place_agent(hazard, pos)

        # ----------------------------------------------------------------
        # Place learning agents
        # ----------------------------------------------------------------
        for _ in range(n_learners):
            pos = next(cell_iter)
            agent = QLearnerAgent(
                self, alpha=alpha, gamma=gamma,
                epsilon_start=epsilon_start,
                epsilon_min=epsilon_min,
                epsilon_decay=epsilon_decay,
            )
            self.grid.place_agent(agent, pos)

        # ----------------------------------------------------------------
        # Place reactive baseline agents
        # ----------------------------------------------------------------
        for _ in range(n_reactive):
            pos = next(cell_iter)
            agent = ReactiveAgent(self)
            self.grid.place_agent(agent, pos)

        self.running = True
        self.datacollector.collect(self)

    def step(self):
        # Environment patches step first (respawn cooldowns)
        self.agents_by_type[RewardPatch].do("step")
        # Then agents (shuffle to avoid order bias)
        self.agents_by_type[QLearnerAgent].shuffle_do("step")
        self.agents_by_type[ReactiveAgent].shuffle_do("step")
        self.datacollector.collect(self)
