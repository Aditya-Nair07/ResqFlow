# Experiment summary — ResQFlow dispatch

**Who this is for:** a quick read for teachers or non-specialists.  
**What we ran:** a fixed, repeatable computer simulation of disaster resource dispatch (no live field data, no AI chat models).  
**Full numbers:** `benchmark_results.csv` (same result every time you re-run).

---

## What we were testing

ResQFlow decides **which rescue unit goes to which emergency**, then **checks safety before sending** the unit.

We compared three ideas:

1. **How to rank units** — four ways to score “best match” (simple weights, ellipse geometry, polygon/hazard geometry, or a mix of all three).
2. **Safety control** — *closed-loop* (check first, fix if unsafe) vs *open-loop* (send the top pick even if checks fail).
3. **Who gets helped first** — GAPD (geometry + urgency + people) vs urgency-only.

We also tried easy and hard map layouts (normal roads, high-risk zones, sparse jobs, low-fuel “stress”).

---

## Key findings (plain language)

### 1. Safety checks matter most when the situation is hard

On a **stress** map (low fuel, long/hard routes):

| Mode | Jobs completed | Times the system had to fix a bad plan | Unsafe sends |
|------|----------------|----------------------------------------|--------------|
| Closed-loop (check before send) | 5 | 1 | **0** |
| Open-loop (send without blocking) | 5 | 0 | **3** |

**Takeaway:** Both modes can finish the same number of jobs, but open-loop still sends units on **3 unsafe** plans. Closed-loop refuses those sends and repairs once instead. Closed-loop also used less travel distance and fuel on this run.

On an easy “default” map, both modes looked the same (no unsafe sends either way). The difference shows up under stress — which is the useful demo point.

### 2. Ranking methods all work on a normal map; differences are small

On the default map with safety checks on:

- All four ranking methods completed **5** assignments and served **2** critical jobs.
- Weighted scoring needed **1** repair and used slightly less fuel.
- Ellipse, polygon, and hybrid needed **0** repairs.

**Takeaway:** Geometry-based ranking is competitive with classic weighted scoring. Big differences appear more in *how* units are chosen and repaired than in raw “jobs done” on this small demo.

### 3. Harder maps force more repairs and higher risk

| Map situation | Jobs done | Repairs | Route risk (higher = worse) | Critical jobs helped |
|---------------|-----------|---------|-----------------------------|----------------------|
| Default (normal) | 5 | 0 | 15.6 | 2 |
| Risk-heavy (bad roads) | 4 | 3 | 57.5 | 1 |
| Sparse (spread out) | 4 | 0 | 1.5 | 2 |
| Stress (low fuel) | 5 | 1 | 17.8 | 2 |

**Takeaway:** When the map is dangerous, the system still tries to help but must **repair plans more often** and accepts higher route risk. That is expected closed-loop behavior, not a failure.

### 4. Priority rule (GAPD vs urgency)

On the default map, both rules produced the **same overall totals** in this spreadsheet. Ordering of individual jobs can still differ; the live UI “Method Compare” view shows that better than these summary totals.

---

## How to say this in one sentence (for a slide or viva)

> In a repeatable simulation, ResQFlow’s closed-loop “verify then send” control avoided unsafe dispatches under stress (0 unsafe vs 3 for open-loop), while geometry-based ranking matched classic weighted scoring on job completion.

---

## What this is *not*

- Not a real disaster or field trial.
- Not a test of the digital-twin web API or an LLM advisor.
- Not proof that one ranking method is always best — only that, on these fixed demo maps, safety control is the clearest win, and ranking methods stay comparable.

To regenerate the CSV: `node experiments/run_benchmarks.js`
