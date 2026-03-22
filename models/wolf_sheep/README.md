# Model 2: Wolf-Sheep Predator-Prey

**Mesa concepts practised:** `MultiGrid`, `agents_by_type`, multi-class stepping order,
two-step agent removal, `DataCollector` with multi-series population tracking

---

## What this model does

Three types of agents share a grid: `GrassPatch` (resource), `Sheep` (herbivore), `Wolf` (predator).

- Sheep eat grass, gain energy, reproduce, and die of starvation
- Wolves eat sheep, gain energy, reproduce, and die of starvation
- Eaten grass patches regrow after a fixed countdown

Under the right parameter regime the model produces sustained oscillating cycles — high sheep population draws wolves in, wolf predation crashes the sheep population, wolves then starve, sheep recover. This is the discrete-space analogue of Lotka-Volterra equations, but the emergent dynamics depend heavily on spatial structure and stochastic effects that the ODE model cannot capture.

---

## Files

| File | Description |
|------|-------------|
| `model.py` | `GrassPatch`, `Sheep`, `Wolf`, `WolfSheepModel` |
| `run.py` | CLI runner, grid snapshots, population time series plot |

---

## How to run

```bash
pip install mesa matplotlib numpy
python run.py
```

Interesting experiments:
```bash
python run.py --wolves 5          # near-extinction start — does the pack recover?
python run.py --wolf_reproduce 0.08 --sheep_reproduce 0.02  # wolves dominate
python run.py --grass_regrowth 5  # fast grass — stabilises sheep boom-bust
python run.py --steps 500 --seed 0  # longer run, different seed
```

---

## What I learned

### `MultiGrid` vs `SingleGrid`
`SingleGrid` enforces one agent per cell — fine for Schelling where agents represent households. `MultiGrid` allows any number of agents per cell, which is essential here because wolves and sheep can occupy the same cell (wolves must be able to catch sheep). The API is identical; the distinction is enforced at placement time only.

### `agents_by_type[ClassName]` — filtered AgentSets
This is one of the cleanest Mesa 3.x additions. Instead of filtering a list yourself:
```python
# Old approach
sheep = [a for a in self.schedule.agents if isinstance(a, Sheep)]

# Mesa 3.x
self.agents_by_type[Sheep]  # returns a live AgentSet view
```
The result supports `.shuffle_do()`, `.do()`, `len()`, and iteration. Very clean.

### `get_neighborhood` vs `get_neighbors` — a gotcha
These two methods sound interchangeable but return completely different things:

| Method | Returns |
|--------|---------|
| `grid.get_neighborhood(pos, moore=True)` | **List of positions** (tuples) |
| `grid.get_neighbors(pos, moore=True)` | **List of agents** at neighbouring cells |

Using `get_neighborhood` and then trying to iterate agents over the result fails silently (you'd be iterating coordinate tuples). Took a debugging pass to catch this. Prefer being explicit with variable names (`possible_moves` vs `neighbouring_agents`).

### `get_cell_list_contents` returns all agent types
```python
self.model.grid.get_cell_list_contents([self.pos])
```
Returns every agent at those cells — wolves, sheep, and grass patches all mixed together. You always need to filter by type explicitly:
```python
sheep_here = [a for a in cell_contents if isinstance(a, Sheep)]
```
An isinstance filter is clear but verbose. Worth thinking about whether a helper like `get_agents_of_type_at(pos, AgentClass)` would be worth adding to `MultiGrid`.

---

## ⚠️ Pain Points & Issues

### PAIN POINT 1 — Two-step agent removal (critical)
**Issue:** In Mesa 3.x, removing an agent requires two separate calls:
```python
self.model.grid.remove_agent(self)   # removes from the spatial grid
self.remove()                         # removes from model.agents / AgentSet
```
Calling only `self.remove()` leaves a ghost agent on the grid. Calling only `grid.remove_agent()` leaves a ghost in the AgentSet. Both ghosts cause subtle bugs — the ghost in the grid means the cell is treated as occupied, and the ghost in the AgentSet means it gets stepped again next turn.

**What would help:** A single `agent.remove()` that handles both, or at minimum a clear warning in the docs when an agent is removed from one structure but not the other. This is a frequent source of confusion for new users and came up immediately when implementing wolf predation.

**Workaround used:** Extracted into a `_die()` helper on each agent class so the two-step pattern is in one place and can't be missed.

---

### PAIN POINT 2 — Stepping order produces measurably different dynamics
**Issue:** The order in which agent types are activated each step is not just an implementation detail — it is a modelling decision that significantly changes outcomes.

In this model, three orderings were tested:

| Order | Effect |
|-------|--------|
| Grass → Sheep → Wolves | Sheep eat before wolves hunt; slightly favours sheep survival |
| Grass → Wolves → Sheep | Wolves eat first; slightly reduces sheep at equilibrium |
| All agents shuffled together | Grass patches get stepped mid-predation round; produces different energy timing |

The "correct" order depends on what the model is trying to represent. Mesa 3.x makes this explicit through the separation of `agents_by_type[X].shuffle_do("step")` calls, but there is no built-in mechanism to document or enforce a chosen ordering. In a collaborative or long-running project, this is a silent assumption that could easily drift.

**What would help:** A convention or optional metadata field for documenting intended activation order in the model class.

---

### PAIN POINT 3 — `agents_by_type` on an empty type
**Issue:** `len(self.agents_by_type[Wolf])` works correctly when wolves exist. When the wolf population hits zero, `agents_by_type[Wolf]` returns an empty `AgentSet` (it does not raise `KeyError`). This is correct behaviour in Mesa 3.x, but it was not obvious from the docs and required testing to confirm.

Earlier in development I added a defensive check:
```python
wolves = self.agents_by_type.get(Wolf, [])  # This is NOT needed in Mesa 3.x
```
That's not the right API — `agents_by_type` does not have a `.get()` method. The correct approach is to use it directly and trust that it returns an empty iterable. But the docs don't make this guarantee explicit.

---

### PAIN POINT 4 — `DataCollector` lambdas iterate the same AgentSet multiple times
**Issue:** In the datacollector:
```python
"grass_patches": lambda m: sum(1 for a in m.agents_by_type[GrassPatch] if a.fully_grown)
```
This iterates the full grass patch list every collection step. At 400 cells, this is fine. At 400×400 it would be expensive. Mesa doesn't provide a way to cache computed reporter values within a step. For models where data collection is expensive, you'd need to maintain counters manually on the model object and update them in `step()`.

---

### PAIN POINT 5 — No built-in population floor / extinction handling
**Issue:** The model halts when wolves or sheep hit zero. But in real runs, populations can drop to 1–2 individuals, which creates extreme stochastic sensitivity — a single bad RNG draw eliminates the species. There's no built-in mechanism to distinguish "ecologically extinct" from "mathematically zero."

This isn't really a Mesa bug — it's an inherent challenge in ABMs — but it would be useful to have a standard pattern for stochastic quasi-extinction (e.g., a minimum viable population threshold).

---

### OBSERVATION — Spatial structure vs ODE dynamics
The Lotka-Volterra ODE predicts smooth, symmetric population cycles. This model produces:
- Spiky, asymmetric oscillations
- Frequent extinction events that the ODE never predicts
- Spatial clustering of wolves around dense sheep pockets

These are emergent from the discrete spatial structure and random movement, not from parameter choices. The same mechanism — local interaction creating macro-level divergence from mean-field predictions — is why ABMs add value over analytical models. The Behavioral Framework project would add another layer on top: agents that *adapt* their behaviour in response to these spatial dynamics.

---

## Parameter stability notes

| Configuration | Typical outcome |
|---------------|-----------------|
| Default (sheep=100, wolves=25) | Sustained cycles for ~200–300 steps before one extinction |
| `wolf_reproduce=0.03` | Wolves die out within ~80 steps; sheep overpopulate |
| `wolf_reproduce=0.08` | Wolves boom and eat all sheep; then starve |
| `grass_regrowth_time=10` | Stable; fast grass sustains sheep through wolf crashes |
| `grass_regrowth_time=60` | Grass becomes bottleneck; both populations crash |
| `seed=7` (default params) | Wolves extinct at ~step 140 |

---

## Connection to Behavioral Framework

Wolf and sheep agents in this model are purely reactive:
- Move randomly (not toward food or away from threats)
- Reproduce probabilistically (not based on condition or goals)
- No memory of past states
- No model of their environment

Behaviorally richer agents would:
- **Sheep:** maintain a *belief* about local wolf density and bias movement away; have a *desire* to balance eating vs safety
- **Wolves:** coordinate pursuit; form packs based on shared *intentions*
- **Both:** adapt reproduction timing based on energy reserves (a simple form of needs-based decision-making)

These are precisely the capabilities the Behavioral Framework aims to add — and this model is a concrete test case where the difference would be observable in population dynamics.
