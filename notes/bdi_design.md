# BDI Architecture Design Notes

Working notes on implementing BDI in Mesa and what it would take to support it natively.

---

## What BDI is (and isn't)

BDI = Belief-Desire-Intention, from Bratman (1987) and formalised for agents by Rao & Georgeff (1995).

The key claim: rational agents can be usefully modelled as having three mental attitudes:

| Attitude | What it represents | Analogy |
|----------|-------------------|---------|
| **Beliefs** | Agent's internal model of the world | "I think there is food at (3,4)" |
| **Desires** | Goals the agent wants to achieve | "I want to have energy > 5" |
| **Intentions** | Committed plans currently being executed | "I will move to (3,4) then collect" |

The critical distinction from reactive agents: **intentions persist**. An agent doesn't re-evaluate everything from scratch each step — it commits to a plan and only reconsiders when the plan fails or a higher-priority desire emerges. This matches how people (and firms) actually behave.

---

## The deliberation cycle

```
perceive()      → update beliefs from environment observations
get_desires()   → return active desires, priority-ordered
deliberate()    → if top desire changed or plan empty → replan
plan(desire)    → generate intention queue for chosen desire
execute()       → pop and run next action from queue
```

One full cycle = one Mesa `step()`.

---

## What I built in bdi_agents/

`bdi_base.py` provides the abstract skeleton. `model.py` instantiates it with a `ForagerAgent` in a grid environment with food patches and a home base.

**ForagerAgent beliefs:**
```python
{
    "energy": float,
    "carrying_food": bool,
    "known_food_locations": set,   # partial — only what's been observed
    "home": tuple,                 # position of home base
    "vision_radius": int,          # how far the agent can see
}
```

**ForagerAgent desires (priority order):**
```python
class ForagerDesire(Enum):
    RETURN_HOME = 1    # if carrying food — highest priority
    FORAGE = 2         # if not carrying and food is known
    EXPLORE = 3        # if not carrying and no known food
    REST = 4           # if energy critically low
```

**Intention actions:**
```python
("MOVE", {"target": (x, y)})
("COLLECT", {"pos": (x, y)})
("DEPOSIT", {})
("RANDOM_MOVE", {})
("WAIT", {})
```

---

## Key design decisions

### 1. Greedy path planning, not A*
`plan()` generates move actions one cell at a time toward the target using Manhattan distance. This is fast and sufficient for demonstrating the architecture. Full A* would be better for obstacle-rich environments.

### 2. Stale belief handling
If a `COLLECT` action fails (food already taken by another agent), `execute_action()` returns `False`. The base class clears the intention queue. On the next step, `perceive()` updates beliefs (removes the now-empty location from `known_food_locations`), then `get_desires()` picks a new desire, then `plan()` replans. This is the core replanning loop working correctly.

### 3. Partial observability via vision radius
Agents only add food locations to `known_food_locations` if within `vision_radius` cells. The grid still *has* the food everywhere — the restriction is in `perceive()`. This is a workaround for Mesa's lack of a native partial observability primitive (pain point #10).

### 4. Intention persistence across steps
The base class only replans when: (a) top desire changes, or (b) queue is empty. This means a MOVE sequence toward food persists across multiple steps without re-evaluating each step. This is what separates BDI from purely reactive agents.

---

## What Mesa currently lacks (and what the Behavioral Framework would add)

### A. `IntentionQueue` as a first-class Mesa primitive
**Current state:** I implemented `deque[tuple[str, dict]]` manually in `bdi_base.py`.
**What's missing:** No standard interface, no Mesa-aware scheduling, no way to interleave intentions from multiple sources.
**Proposed API:**
```python
class IntentionQueue:
    def push(self, action: str, args: dict, priority: int = 0) -> None
    def pop(self) -> tuple[str, dict]
    def peek(self) -> tuple[str, dict] | None
    def clear(self) -> None
    def is_empty(self) -> bool
```

### B. Partial observability support
**Current state:** `grid.get_cell_list_contents([pos])` works for any cell regardless of agent location. Partial observability must be enforced manually in `perceive()`.
**What's missing:** A `vision_radius` filter, or a `grid.get_visible_cells(agent, radius)` method.
**Proposed API:**
```python
grid.get_visible_contents(agent, radius=3, mode="moore")
# Returns only cells within radius of agent.pos
```

### C. Belief store with change detection
**Current state:** `self.beliefs` is a plain Python dict. No history, no change events.
**What's missing:** When beliefs change, desires may need re-evaluation. Currently this requires manual checks.
**Proposed API:**
```python
class BeliefStore(dict):
    def on_change(self, key: str, callback: Callable) -> None
    # callback fires when beliefs[key] changes value
```

### D. Desire representation with preconditions
**Current state:** `get_desires()` is a plain method that returns a list. No formal preconditions.
**What's missing:** A declarative way to define when a desire is active.
**Proposed pattern:**
```python
@desire(precondition=lambda b: b["energy"] < 5, priority=10)
def find_food(self): ...
```

---

## Connection to Boldt (2024) / Mesa Behavioral Framework proposal

The GSoC project references three pillars:
1. **BDI architectures** — this is what `bdi_base.py` prototypes
2. **Needs-based decision-making** (Maslow-style priority hierarchies) — desire ordering is a direct analogue; the `ForagerDesire` enum is a simplified version
3. **Reinforcement learning** — see Model 5 for Q-learning prototype

The pain points above (#9, #10 especially) are the concrete gaps the project should close.

---

## Reading list

- Rao, A.S. & Georgeff, M.P. (1995). BDI agents: from theory to practice. *ICMAS*.
- Bratman, M. (1987). *Intention, Plans, and Practical Reason*. Harvard.
- Wooldridge, M. (2009). *An Introduction to MultiAgent Systems*. Wiley. (Ch. 2–3)
- Mesa docs: https://mesa.readthedocs.io
