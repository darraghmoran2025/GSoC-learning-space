# Model 4: BDI Agent Prototype

**Mesa concepts practised:** custom agent architecture, `SingleGrid` collision as plan invalidation, `agents_by_type`, `DataCollector` capturing internal agent state, `agent.remove()` + `grid.remove_agent()`

---

## What this model does

Implements the **Belief-Desire-Intention (BDI)** cognitive architecture in Mesa and applies it to a foraging scenario: agents navigate a grid, locate food using partial vision, collect it, and deposit it at a shared home base.

This is a proof-of-concept for the kind of agent internal structure that the GSoC Behavioral Framework project aims to support natively in Mesa.

---

## Files

| File | Description |
|------|-------------|
| `bdi_base.py` | Abstract `BDIAgent` base class — reusable, domain-agnostic |
| `model.py` | `ForagerAgent` (concrete BDI agent), `FoodPatch`, `ForagingModel` |
| `run.py` | Animated grid runner with desire distribution time series |

---

## How to run

```bash
pip install mesa matplotlib
python run.py                   # default: 10 foragers, 60 food, 120 steps
python run.py --foragers 20     # more agents (more collisions, more replanning)
python run.py --vision 1        # near-blind agents — mostly EXPLORE
python run.py --vision 8        # wide vision — agents go mostly straight to food
python run.py --no-plot         # headless stats only
```

---

## Architecture

### The BDI cycle (one step)

```
perceive()    →  update beliefs from environment
deliberate()  →  pick highest-priority desire; replan if desire changed or queue empty
execute()     →  pop and run next action from intention queue; clear queue on failure
```

### Beliefs

| Key | Type | Description |
|-----|------|-------------|
| `energy` | int | Current energy level |
| `carrying_food` | bool | Whether holding a food item |
| `known_food` | set of (x,y) | Grid positions where food was last seen |
| `home` | (x,y) | Home base — never changes |

### Desires (priority order)

| Desire | Condition | Plan generated |
|--------|-----------|----------------|
| `REST` | energy ≤ 5 | Single WAIT action (+2 energy) |
| `RETURN_HOME` | carrying food | Greedy path to home + DEPOSIT |
| `FORAGE` | known_food non-empty | Greedy path to nearest food + COLLECT |
| `EXPLORE` | no known food | 6-step random walk |

### Intentions

Each plan is a `deque` of `(action_name, args)` tuples executed one per step:

```
("MOVE",    {"target": (x, y)})
("COLLECT", {"expected_pos": (x, y)})
("DEPOSIT", {})
("WAIT",    {})
```

Replanning is triggered automatically when:
- The top desire changes (e.g. agent picks up food → switches to RETURN_HOME)
- The intention queue empties
- An action returns `False` (e.g. MOVE is blocked by another agent; COLLECT finds no food)

---

## What I learned

### BDI separates *what to do* from *how to do it*

In every previous model, agent logic was a single `step()` function. BDI forces a clean split:
- `get_desires()` — strategic level: what does the agent want?
- `plan()` — tactical level: what sequence of actions achieves that?
- `execute_action()` — operational level: how is each primitive action carried out?

This separation is immediately useful. Changing forager strategy (e.g. always prioritise rest over foraging) only requires changing `get_desires()`. Changing how movement works only requires changing `execute_action("MOVE", ...)`. The two concerns don't mix.

### Stale beliefs are a core modelling challenge

The most interesting bugs all involved stale beliefs — food the agent *believed* was there but had already been eaten. This forced the model to handle COLLECT returning `False` and correctly triggering a replan.

This is directly relevant to the Behavioral Framework: any implementation of beliefs in Mesa needs to handle belief revision (removing outdated entries) as a first-class concern, not an afterthought.

### Plan invalidation via action failure

Using MOVE collision (`return False`) to trigger automatic replanning turned out to be a clean pattern. The agent doesn't need to check if its plan is still valid — it just tries the next step, and if it fails, replans from the current state. This is the essence of the BDI "reactive planning" model.

### DataCollector capturing internal agent state

Tracking `desire`, `carrying_food`, and `replans` per agent per step via `agent_reporters` gives a much richer picture than model-level summaries. The desire distribution over time (stacked area chart) was particularly informative — you can see the population shift from EXPLORE → FORAGE as agents begin discovering food, then RETURN_HOME spikes as they fill up.

---

## Experiments

| Vision range | Avg replans/agent (120 steps) | Dominant desire |
|---|---|---|
| 1 (near-blind) | ~45 | EXPLORE → FORAGE (late) |
| 3 (default)    | ~18 | FORAGE + RETURN_HOME balanced |
| 6 (wide)       | ~8  | FORAGE dominates from step 2 |
| 8 (very wide)  | ~5  | Near-optimal path planning |

Vision range is the single biggest driver of efficiency. This maps to an information asymmetry argument: agents with better beliefs need less replanning.

---

## Pain Points

### #9 — No built-in support for multi-step plans or deferred actions

Mesa's agent model is strictly one `step()` call per step. There is no mechanism for an agent to say "I want to take these 5 actions over the next 5 steps." The BDI base class works around this with a `deque` of intentions that persists across steps, but this is entirely user-managed state.

A native `IntentionQueue` or `Plan` object in Mesa would allow the scheduler to manage this, enable pausing/resuming plans, and make serialisation of agent state possible.

**Impact:** High for any behaviorally complex model. This is the core gap the Behavioral Framework project addresses.

---

### #10 — Partial observability requires manual implementation

Mesa grids expose complete information: `grid.get_cell_list_contents([pos])` works for *any* position, not just positions within an agent's sight range. Enforcing partial observability (agents can only perceive nearby cells) is entirely the modeller's responsibility.

This required writing a `perceive()` method that manually queries only cells within `vision_range` and explicitly discards stale beliefs. There is no Mesa primitive for "what does this agent see from here."

**Impact:** High. Most realistic behavioural models require partial observability. A `PerceptionField` abstraction would be a valuable addition to Mesa.

---

### #11 — `agents_by_type` raises `KeyError` when a type has been fully removed

If all `ForagerAgent` instances die during a run, `model.agents_by_type[ForagerAgent]` raises a `KeyError` rather than returning an empty `AgentSet`. This caused a crash in early runs before adding the `if not list(model.agents_by_type[ForagerAgent])` guard.

The safer API would be to return an empty `AgentSet` for absent types, matching the behaviour of `dict.get()`.

**Impact:** Medium. Reproducible whenever a model allows full population extinction.

---

### #12 — No standard way to serialise or inspect agent beliefs/intentions

Beliefs are just a Python dict and intentions are a deque — there is no Mesa-native introspection mechanism. Debugging requires manually printing agent internals or adding everything to `DataCollector`.

For the Behavioral Framework, a standard `agent.describe()` or `agent.belief_state` interface would make debugging and logging significantly easier.

**Impact:** Medium for development, high for research reproducibility.

---

## Direct relevance to the Behavioral Framework GSoC project

This model is essentially a hand-built prototype of what the Behavioral Framework aims to provide natively:

| What I built manually | What the BF project would provide |
|---|---|
| `BDIAgent` base class in `bdi_base.py` | Native `BDIAgent` in `mesa.agents` |
| `beliefs` dict with manual update logic | Structured belief revision with staleness handling |
| `deque` of `(action, args)` intentions | Native `Plan` / `IntentionQueue` object |
| Manual partial observability in `perceive()` | `PerceptionField` primitive |
| `get_desires()` returning priority list | Declarative goal/desire specification |

The pain points documented here (#9–#12) are the concrete gaps the project needs to fill.
