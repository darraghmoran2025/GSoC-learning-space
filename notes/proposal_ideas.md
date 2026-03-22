# GSoC 2026 Proposal Notes — Mesa Behavioral Framework

Working notes for drafting the proposal. Not polished — thinking out loud.

---

## Project summary (one paragraph)

Mesa is the leading Python framework for agent-based modelling, but its agents are currently memoryless and reactive. The Behavioral Framework project adds the internal cognitive structure — beliefs, desires, intentions, needs, and learning — that makes bounded rationality modelable rather than just acknowledged. I will implement a `BDIAgent` base class, a `NeedsAgent` base class, and a Q-learning mixin, along with the supporting Mesa primitives (IntentionQueue, partial observability, BeliefStore) that make these architectures first-class citizens of the framework.

---

## Gap → Deliverable mapping (pain points #9–#12 → API)

This is the key table for the proposal. Each gap from the pain points log maps directly to a concrete deliverable.

| Pain Point | Gap | Proposed Deliverable | How it changes model code |
|------------|-----|----------------------|--------------------------|
| #9 | No built-in multi-step plan / deferred action mechanism — intention queues must be user-managed | `mesa.behavioral.IntentionQueue` — a Mesa-aware deque with priority support, step scheduling, and failure handling | Replace `from collections import deque` + manual action dispatch with `from mesa.behavioral import IntentionQueue`; `agent.intentions.push("MOVE", {"target": pos})`; Mesa handles pop/execute loop |
| #10 | No partial observability primitive — any agent can read any cell | `grid.get_visible_contents(agent, radius, mode)` — returns only cells within the agent's vision radius | Replace manual `[a for a in grid.get_cell_list_contents([pos]) if distance(pos, agent.pos) <= r]` with `grid.get_visible_contents(self, radius=3)` |
| #11 | `agents_by_type[T]` raises `KeyError` when all agents of type T removed | Fix `agents_by_type` to return empty `AgentSet` on missing key (one-line fix + regression test) | Removes try/except boilerplate from any model that handles extinction events |
| #12 | No standard interface for inspecting belief/intention state | `DataCollector` integration for BDI state — `agent_reporters` that can introspect `beliefs`, `intentions`, `current_desire` | `DataCollector(agent_reporters={"current_desire": "current_desire", "n_intentions": lambda a: len(a.intentions)})` works out of the box |

---

## Three pillars and what I've built for each

### Pillar 1: BDI architecture
- **Built:** `bdi_base.py` — abstract `BDIAgent` with full deliberation cycle
- **Built:** `ForagerAgent` — concrete BDI agent with beliefs, 4 desires, greedy path planning, stale belief handling
- **Proposal deliverable:** Port `bdi_base.py` into `mesa.behavioral.BDIAgent`, add IntentionQueue, add partial observability

### Pillar 2: Needs-based decision-making
- **Analogue in existing work:** `ForagerDesire` enum with priority ordering is structurally identical to a Maslow hierarchy
- **Proposal deliverable:** `mesa.behavioral.NeedsAgent` — desires defined as `Need` objects with satiation curves, deficiency drives, and automatic priority reordering. Scenario: economic agent with needs for liquidity, security, growth (maps directly to my financial background)

### Pillar 3: Reinforcement learning
- **Built:** Model 5 (`models/rl_agent/`) — Q-learning agent on a grid
- **Proposal deliverable:** `mesa.behavioral.RLAgent` mixin with pluggable policy (Q-table, epsilon-greedy, policy gradient stub)

---

## Scope question for mentors

The proposal currently covers all three pillars. If mentors feel that's too broad for one summer, my priority order is:
1. BDI + IntentionQueue + partial observability (most novel, most requested)
2. Needs-based agent (clean extension of BDI desire framework)
3. RL mixin (most self-contained, lowest risk)

Happy to cut pillar 3 if it would make the other two deeper.

---

## Timeline sketch (12 weeks)

| Week | Work |
|------|------|
| 1–2 | Community bonding: finalise API design with mentors, write ADR (Architecture Decision Record) |
| 3–4 | `IntentionQueue` + `BeliefStore` primitives, tests |
| 5–6 | `BDIAgent` base class in mesa.behavioral, port ForagerAgent as example |
| 7 | Partial observability (`get_visible_contents`), tests |
| 8 | `NeedsAgent` base class + example (economic scenario) |
| 9–10 | Q-learning mixin + GridWorld example |
| 11 | Documentation, tutorials, integration tests |
| 12 | Buffer / stretch goals / PR review |

---

## Things to look up before submitting

- [ ] Check Mesa contributing guide for preferred PR structure
- [ ] Check if IntentionQueue has been discussed in Mesa issues already (search: "intention", "plan", "BDI")
- [ ] Look at Mesa's existing `experimental/` directory — anything BDI-adjacent?
- [ ] Find the Mesa Zulip / Discord and introduce myself before the proposal deadline
- [ ] Read the Mesa 3.x changelog carefully — some of my "pain points" may already be fixed in main

---

## Proposal structure (draft outline)

1. **Abstract** (250 words) — problem, solution, impact
2. **About me** — Financial Maths + Economics, actuarial internship, trading competitions, why ABMs
3. **Why this project** — MoneyModel gap, Black Swan, poker/markets as bounded rationality examples
4. **Technical proposal**
   - Current state of Mesa agents (reactive, memoryless)
   - Three pillars: BDI, needs, RL
   - Gap → deliverable table (from above)
   - API sketches with before/after code examples
5. **Prior work** — this repo: 4 models, bdi_base.py, pain points log
6. **Timeline** — week-by-week
7. **About me** (expanded) — relevant coursework, Python experience, open source experience
