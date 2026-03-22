"""
BDI Agent Base Class for Mesa
================================
Implements the Belief-Desire-Intention (BDI) cognitive architecture
as an abstract Mesa agent base class.

BDI overview:
  Beliefs   — the agent's internal model of the world (what it thinks is true)
  Desires   — goals the agent would like to achieve (what it wants)
  Intentions — committed plans the agent is currently executing (what it will do)

The deliberation cycle each step:
  1. perceive()    — observe the environment, update beliefs
  2. deliberate()  — choose which desire to pursue given current beliefs;
                     replan if the top desire has changed or the plan is empty
  3. execute()     — carry out the next action in the intention queue;
                     if the action fails, clear the queue (triggers replan next step)

Design notes:
  - beliefs is a plain dict; keys are strings, values are anything
  - desires are returned as a priority-ordered list by get_desires()
  - intentions is a deque of (action_name: str, args: dict) tuples
  - Replanning is triggered automatically when:
      * current desire changes
      * intention queue runs empty
      * an action returns False (failure)
  - Subclasses implement perceive(), get_desires(), plan(), execute_action()

This base class deliberately adds zero domain logic — it is a framework
skeleton. All domain knowledge lives in the subclass.
"""

from abc import ABC, abstractmethod
from collections import deque
from typing import Any


class BDIAgent(ABC):
    """
    Abstract BDI agent base class for Mesa.

    Usage:
        class MyAgent(BDIAgent, mesa.Agent):
            def __init__(self, model):
                mesa.Agent.__init__(self, model)
                BDIAgent.__init__(self)

            def perceive(self): ...
            def get_desires(self): ...
            def plan(self, desire): ...
            def execute_action(self, action, args): ...
    """

    def __init__(self):
        # Core BDI state
        self.beliefs: dict[str, Any] = {}
        self.current_desire = None
        self.intentions: deque[tuple[str, dict]] = deque()

        # Diagnostics — useful for data collection and debugging
        self.bdi_stats = {
            "replans": 0,         # how many times the agent has replanned
            "failed_actions": 0,  # actions that returned False
            "steps_idle": 0,      # steps with empty intention queue
        }

    # ------------------------------------------------------------------
    # Abstract interface — subclass must implement these four methods
    # ------------------------------------------------------------------

    @abstractmethod
    def perceive(self) -> None:
        """
        Observe the environment and update self.beliefs.

        Called first in every step. Should be a read-only operation
        (no side effects on the environment).

        Example:
            self.beliefs["energy"] = self.energy
            self.beliefs["food_visible"] = self._scan_for_food()
        """

    @abstractmethod
    def get_desires(self) -> list:
        """
        Return the agent's currently active desires, highest priority first.

        Called during deliberation. Should use self.beliefs only —
        do not read the environment directly here.

        Returns:
            list of desire values (e.g. members of an Enum)
            Empty list means the agent has nothing to do.

        Example:
            desires = []
            if self.beliefs["energy"] < 5:
                desires.append(Desire.FIND_FOOD)
            return desires
        """

    @abstractmethod
    def plan(self, desire) -> deque:
        """
        Generate an intention sequence (plan) for the given desire.

        Returns:
            deque of (action_name: str, args: dict) tuples.
            The agent will execute these one per step, left to right.

        Example:
            if desire == Desire.FIND_FOOD:
                path = self._path_to(nearest_food)
                q = deque(("MOVE", {"target": p}) for p in path)
                q.append(("COLLECT", {"pos": nearest_food}))
                return q
        """

    @abstractmethod
    def execute_action(self, action: str, args: dict) -> bool:
        """
        Execute a single action from the intention queue.

        Args:
            action: action name string (e.g. "MOVE", "COLLECT", "WAIT")
            args: parameters for the action

        Returns:
            True  — action succeeded, continue with next intention
            False — action failed, intention queue will be cleared
                    and the agent will replan next step
        """

    # ------------------------------------------------------------------
    # BDI deliberation cycle — called by step()
    # ------------------------------------------------------------------

    def _deliberate(self) -> None:
        """
        Select which desire to pursue.

        Keeps the current plan if:
          - the top desire is unchanged AND
          - the intention queue is non-empty

        Replans if any of those conditions is not met.
        """
        desires = self.get_desires()

        if not desires:
            self.current_desire = None
            self.intentions.clear()
            self.bdi_stats["steps_idle"] += 1
            return

        top_desire = desires[0]

        needs_replan = (
            self.current_desire != top_desire
            or len(self.intentions) == 0
        )

        if needs_replan:
            self.current_desire = top_desire
            self.intentions = self.plan(top_desire)
            self.bdi_stats["replans"] += 1

    def _execute(self) -> None:
        """Pop and execute the next intention. Clear queue on failure."""
        if not self.intentions:
            self.bdi_stats["steps_idle"] += 1
            return

        action, args = self.intentions.popleft()
        success = self.execute_action(action, args)

        if not success:
            self.intentions.clear()
            self.bdi_stats["failed_actions"] += 1

    # ------------------------------------------------------------------
    # Main step — subclass can override but should call super().bdi_step()
    # ------------------------------------------------------------------

    def bdi_step(self) -> None:
        """
        Run one full BDI deliberation cycle.
        Call this from your Mesa agent's step() method.
        """
        self.perceive()
        self._deliberate()
        self._execute()
