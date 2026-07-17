# ResQFlow dispatch experiments

Offline, deterministic benchmarks of the auction dispatch core (geometry ranking, GAPD priority, verify-then-actuate). **No LLM, no network, fixed layouts.**

## Run

```bash
node experiments/run_benchmarks.js
```

Writes `experiments/results/benchmark_results.csv`. Re-runs produce identical CSV (seed `42`, no RNG).

## Metrics (7)

| Column | Meaning |
|--------|---------|
| `assignments` | Successful dispatches |
| `repairs` | Closed-loop transactional repairs after a failed verify |
| `unsafe_actuations` | Actuations that would fail the 8-check gate (open-loop only) |
| `avg_distance` | Mean unit→incident distance for assignments |
| `avg_route_risk` | Mean route risk score for assignments |
| `total_fuel_cost` | Sum of estimated fuel used |
| `critical_served` | Critical-band incidents served |

Identity columns: `case_id`, `ranking_method`, `control_mode`, `priority_mode`, `scene`, `seed`.

## Cases

- **Methods:** weighted / ellipse / polygon / hybrid (closed + GAPD, default scene)
- **Control:** closed vs open on default; closed vs open on **stress** (low fuel + hard routes)
- **Priority:** GAPD vs urgency-only
- **Scenes:** default, risk_heavy, sparse, stress

## Honesty

These are **simulation-plant** results from a Node harness that mirrors `index.html` scoring/verify/GAPD logic. They are not field measurements or digital-twin API runs. Use for method/control contrasts in demos and papers, with that caveat stated.
