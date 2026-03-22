# Motivation

**Name:** Darragh Moran
**University:** University of Galway
**Degree:** Financial Mathematics & Economics (Third Year)
**GSoC 2026 Project:** Mesa — Behavioral Framework

---

## Background

My degree sits at the intersection of mathematics, statistics, and economics, with coursework in Game Theory, Stochastic Processes, and Econometrics. I'm currently completing an actuarial internship, where I've built quantitative tools in Python using Pandas, Matplotlib, NumPy, SciPy, and Seaborn. I also have a solid foundation in C++ and R, and have done smaller-scale projects in TypeScript and HTML.

Outside the classroom: I co-founded my university's Student Managed Fund and won two national trading competitions (CME, Euronext). That experience; watching real market behaviour diverge sharply from what textbooks predict; is a large part of what drew me here.

---

## Why Mesa and the Behavioral Framework

My degree has trained me to think in terms of rational agents: Nash equilibria, expected utility, efficient markets. But everything I've done outside the classroom has pushed back against that.

Poker taught me that real decision-making is shaped by incomplete information, risk perception, and adaptation under pressure. Trading competitions showed me how quickly market behaviour diverges from what theory predicts. Reading *The Black Swan* reframed how I think about tail risk and the limits of models that assume agents process the world correctly.

Mesa's MoneyModel made that tension concrete. Working through the tutorial, the agents are effectively memoryless — they transfer wealth randomly, with no goals, no learning, no sense of what they're trying to achieve. It works as a demonstration of emergent inequality, but it's a long way from modelling how people actually behave in economic systems.

The Behavioral Framework is the project that closes that gap. Implementing BDI architectures, needs-based decision-making, and reinforcement learning would give Mesa agents the kind of internal structure that makes bounded rationality modelable rather than just acknowledged.

---

## Learning Goals for This Space

1. Build fluency with Mesa's core abstractions: agents, model, scheduler, grid, data collection
2. Understand how agent state and decision logic interacts with emergent system-level behaviour
3. Build progressively more complex models, starting with classic ABMs and moving toward behaviorally richer agents
4. Develop a clear sense of where the current framework ends and where the Behavioral Framework begins

---

## Models Planned

| # | Model | Key concept | Status |
|---|-------|-------------|--------|
| 1 | Schelling Segregation | `SingleGrid`, agent preferences, emergent spatial patterns | ✅ Complete |
| 2 | Wolf-Sheep Predator-Prey | `MultiGrid`, multi-type agents, energy/removal, Lotka-Volterra dynamics | ✅ Complete |
| 3 | Wealth Distribution (extended) | Gini coefficient, network effects, richer data collection | ✅ Complete |
| 4 | BDI Agent prototype | Belief-Desire-Intention architecture in Mesa | ✅ Complete |
| 5 | RL Agent (Q-learning) | Tabular Q-learning, ε-greedy exploration, value heatmap, learner vs. reactive comparison | ✅ Complete |

---

## Status

- [x] Schelling Segregation — complete
- [x] Wolf-Sheep Predator-Prey — complete
- [x] Wealth Distribution (extended) — complete
- [x] BDI Agent prototype — complete
- [x] RL Agent (Q-learning) — complete

---

## Pain Points Log

Issues and observations worth raising with the Mesa community:

| # | Issue | Model found in | Severity |
|---|-------|---------------|----------|
| 1 | Two-step agent removal (`grid.remove_agent` + `agent.remove()`) is easy to get half-wrong, leaving ghost agents | Wolf-Sheep | High |
| 2 | Stepping order between agent types is a silent modelling assumption with measurable outcome effects — no built-in way to document it | Wolf-Sheep | Medium |
| 3 | `get_neighborhood` vs `get_neighbors` return types (positions vs agents) are easy to confuse | Wolf-Sheep | Medium |
| 4 | `DataCollector` lambdas re-iterate AgentSets every step — no caching mechanism for expensive reporters | Wolf-Sheep | Low (at scale: High) |
| 5 | `agents_by_type` behaviour on zero-population types not clearly documented | Wolf-Sheep | Low |
| 6 | `NetworkGrid.coord_iter()` not implemented — must fall back to raw NetworkX graph | Wealth | Medium |
| 7 | `get_agent_vars_dataframe()` returns multi-indexed `(Step, AgentID)` frame with no clear docs example | Wealth | Medium |
| 8 | `NetworkGrid.get_neighbors()` silently returns `[]` for isolated nodes — no warning | Wealth | Low |
| 9 | No built-in multi-step plan / deferred action mechanism — intention queues must be user-managed | BDI | High |
| 10 | No partial observability primitive — `grid.get_cell_list_contents()` works for any cell regardless of agent position | BDI | High |
| 11 | `agents_by_type[T]` raises `KeyError` when all agents of type T have been removed | BDI | Medium |
| 12 | No standard interface for inspecting agent belief/intention state — all debugging is manual | BDI | Medium |
| 13 | No built-in state abstraction for RL — state is just `agent.pos`; adding features requires manual tuple-packing | RL Agent | Medium |
| 14 | Q-table not serialisable via `DataCollector` — can't track full policy evolution over time without custom serialisation | RL Agent | Medium |
| 15 | `SingleGrid` prevents multiple agents per cell — distorts learned policy in dense RL environments | RL Agent | Low |
| 16 | `mesa.space` is deprecated in favour of `mesa.discrete_space` but the migration path and API differences aren't clearly documented — flagged by a maintainer during a community discussion | All models | Medium |
