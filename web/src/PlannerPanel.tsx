import { useEffect, useState } from 'react';
import { Check, RefreshCw } from 'lucide-react';
import { api, type Snapshot } from './api';

/**
 * Planner tab — honest "what-if" comparison of the three dispatch strategies
 * over the exact same plant state. Operator picks one and commits it; Run
 * continues from there. Compare/commit rules are backend-authoritative.
 */
export default function PlannerPanel({
  plans,
  scenarioId,
  tick,
  snap,
  rankingMethod,
  onMessage,
  onPlans,
  onRefresh,
}: {
  plans: any | null;
  scenarioId: string;
  tick: number;
  snap: Snapshot;
  rankingMethod: string;
  onMessage: (message: string) => Promise<void>;
  onPlans: (plans: any) => void;
  onRefresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const scarceOn = Boolean(snap.scarceSeats);

  useEffect(() => {
    if (plans?.recommendedPlanId) setExpanded(plans.recommendedPlanId);
  }, [plans?.recommendedPlanId]);

  const waiting = snap.groups
    .filter((g) => !['RESOLVED', 'REJECTED', 'DUPLICATE', 'evacuated'].includes(g.status))
    .reduce((sum, g) => sum + Math.max(0, (g.people || 0) - (g.evacuatedPeople || 0)), 0);
  const waitingGroups = snap.groups.filter(
    (g) => !['RESOLVED', 'REJECTED', 'DUPLICATE', 'evacuated'].includes(g.status),
  ).length;
  const freeUnits = (snap.vehicles || []).filter((v) => v.status === 'available').length;
  const totalSeats = (snap.shelters || []).reduce(
    (sum, s) => sum + Math.max(0, (s.capacity || 0) - (s.occupancy || 0) - (s.reservedCapacity || 0)),
    0,
  );
  const reserved = (snap.reservations || []).filter((r) => r.status === 'RESERVED');

  async function compute() {
    setBusy('compute');
    try {
      const result = await api.comparePlans({ scenarioId, rankingMethod });
      onPlans(result);
      await onMessage(result.explanation || 'Plans ready — compare and pick one.');
    } catch (err) {
      await onMessage(`Compare failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(null);
    }
  }

  async function toggleScarce(next: boolean) {
    setBusy('scarce');
    try {
      await api.scarceSeats({ scenarioId, enabled: next });
      onPlans(null);
      await onRefresh();
      await onMessage(
        next
          ? 'Scarce seats ON — shelter seats and fuel are limited. Recompute to see strategies rescue different numbers.'
          : 'Scarce seats OFF — full seats and fuel restored. Recompute for the normal equal-rescue comparison.',
      );
    } catch (err) {
      await onMessage(`Scarce seats toggle failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(null);
    }
  }

  async function approve(plan: any) {
    if (!plan || !plans) return;
    setBusy(plan.planId);
    try {
      const result = await api.approvePlan(plan.planId, {
        scenarioId,
        planId: plan.planId,
        planVersion: plan.planVersion ?? plans.planVersion,
        tick,
        actor: 'operator',
      });
      await onRefresh();
      const target = plan.projectedRescued ?? 0;
      await onMessage(
        `Committed ${plan.planName.replace(/_/g, ' ')} — ${result.committed?.length || 0} unit(s) sent now. `
          + `Press Run and this plan will rescue ${target} people.`,
      );
      onPlans(null);
    } catch (err) {
      await onMessage(`Commit failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(null);
    }
  }

  const list: any[] = plans?.plans || [];
  const recommendedId = plans?.recommendedPlanId;

  return (
    <section className="planner-tab panel">
      <div className="panner-heading planner-heading">
        <div>
          <p className="eyebrow">PLANNER (WHAT-IF)</p>
          <h2>Compare rescue strategies</h2>
          <span>
            Same flood, three strategies. Each number is exactly how many people that plan rescues once you
            commit it and press Run — pick the one you want.
          </span>
        </div>
        <div className="planner-heading-actions">
          <label className={`scarce-toggle ${scarceOn ? 'on' : ''}`}>
            <input
              type="checkbox"
              checked={scarceOn}
              disabled={busy === 'scarce'}
              onChange={(e) => void toggleScarce(e.target.checked)}
            />
            <span>Scarce seats (demo)</span>
          </label>
          <button
            className="compute-button"
            type="button"
            disabled={busy === 'compute'}
            onClick={() => void compute()}
          >
            <RefreshCw size={16} /> {list.length ? 'Recompute' : 'Compute plans'}
          </button>
        </div>
      </div>

      <div className="planner-situation">
        <div><small>Still waiting</small><b>{waiting}</b><em>{waitingGroups} groups</em></div>
        <div><small>Free units</small><b>{freeUnits}</b><em>of {snap.vehicles?.length || 0}</em></div>
        <div>
          <small>Shelter seats</small>
          <b className={scarceOn ? 'warn' : ''}>{totalSeats}</b>
          <em>{scarceOn ? 'scarce demo on' : `${snap.shelters?.length || 0} shelters`}</em>
        </div>
        <div><small>Ranking</small><b>{rankingMethod}</b><em>Flood-GAPD + 8-check</em></div>
      </div>

      {scarceOn && (
        <div className="planner-note scarce-note">
          Scarce seats demo: limited shelter capacity and fuel. The three strategies should now show
          <b> different</b> rescue totals — compare who saves more vs who keeps a reserve.
        </div>
      )}

      {!list.length && (
        <p className="planner-empty">
          Press <b>Compute plans</b>. Three strategies (FASTEST, MAX COVERAGE, SAFE &amp; FAIR) will
          run on the same map so you can compare rescued count, speed, and reserves before committing.
        </p>
      )}

      {plans?.explanation && list.length ? (
        <div className="planner-note">{plans.explanation}</div>
      ) : null}

      {list.length ? (
        <div className="plan-cards">
          {list.map((plan: any) => {
            const isRecommended = plan.planId === recommendedId;
            const rescued = plan.projectedRescued ?? 0;
            const leftBehind = plan.projectedStranded ?? 0;
            const isOpen = expanded === plan.planId;
            const noPlan = !(plan.assignments || []).length && !rescued;
            return (
              <article
                key={plan.planId}
                className={`plan-card ${isRecommended ? 'recommended' : ''} ${noPlan ? 'empty' : ''}`}
              >
                <header className="plan-card-head">
                  <p className="eyebrow">{isRecommended ? '★ RECOMMENDED' : 'STRATEGY'}</p>
                  <h3>{plan.planName.replace(/_/g, ' ')}</h3>
                  <small>{plan.goal}</small>
                </header>

                <div className="plan-headline">
                  <span className="ph-label">Rescues</span>
                  <b>{rescued}</b>
                  <span className="ph-unit">people</span>
                  {plan.projectedTicks != null && (
                    <span className="ph-sub">finishes in about {plan.projectedTicks} ticks</span>
                  )}
                </div>

                <ul className="plan-facts">
                  <li>
                    <small>Units sent now</small>
                    <b>{plan.assignments?.length || 0}</b>
                    <em>{plan.vehiclesLeftInReserve ?? 0} kept in reserve</em>
                  </li>
                  <li>
                    <small>First pickup</small>
                    <b>{plan.firstPickupTicks != null ? `${plan.firstPickupTicks}t` : '—'}</b>
                    <em>{plan.avgPickupTicks != null ? `avg ${plan.avgPickupTicks}t` : ''}</em>
                  </li>
                  <li>
                    <small>Groups helped</small>
                    <b>{plan.assignments?.length || 0}</b>
                    <em>of {plan.totalWaitingGroups ?? waitingGroups} waiting</em>
                  </li>
                  <li>
                    <small>Left behind</small>
                    <b className={leftBehind ? 'warn' : ''}>{leftBehind}</b>
                    <em>{leftBehind ? 'no safe route in time' : 'everyone reachable'}</em>
                  </li>
                </ul>

                <p className="plan-tradeoff">{plan.tradeoff}</p>

                <div className="plan-actions">
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => setExpanded(isOpen ? null : plan.planId)}
                  >
                    {isOpen ? 'Hide assignments' : 'Show assignments'}
                  </button>
                  <button
                    type="button"
                    className="approve-action"
                    disabled={noPlan || busy === plan.planId}
                    onClick={() => void approve(plan)}
                  >
                    <Check size={14} /> {busy === plan.planId ? 'Committing…' : 'Commit this plan'}
                  </button>
                </div>

                {isOpen && (
                  <div className="plan-detail">
                    {(plan.assignments || []).length ? (
                      <ul>
                        {plan.assignments.map((a: any) => {
                          const group = snap.groups.find((g) => g.id === a.groupId);
                          const shelter = snap.shelters.find((s) => s.id === a.shelterId);
                          const vehicle = snap.vehicles.find((v) => String(v.id) === String(a.vehicleId));
                          const pickup = a.pathPickup?.travelTime;
                          const seats = a.load ?? 0;
                          return (
                            <li key={`${a.groupId}-${a.vehicleId}`}>
                              <b>{group?.label || a.groupId}</b>
                              <span>
                                {vehicle?.type || `Unit ${a.vehicleId}`} → {shelter?.label || a.shelterId}
                                {' · '}
                                {seats} seats
                                {pickup != null ? ` · pickup in ${pickup}t` : ''}
                                {' · '}
                                {a.verification?.passed ? '8/8 checks' : (a.verification?.failed || []).join(', ') || 'unverified'}
                              </span>
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="plan-empty">
                        No safe assignments could be built for this strategy right now.
                        Try Run for a tick to let flooded routes settle, then Recompute.
                      </p>
                    )}
                    {plan.rejected?.length ? (
                      <p className="plan-warn">
                        Unreachable this round: {plan.rejected.map((r: any) => `${r.groupId} (${r.reason})`).join(' · ')}
                      </p>
                    ) : null}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      ) : null}

      <div className="ledger planner-ledger">
        <div className="planner-subheading">
          <b>RESERVATION LEDGER</b>
          <span>{reserved.length ? `${reserved.length} active` : 'None active'}</span>
        </div>
        {reserved.length === 0 ? (
          <p className="planner-empty subtle">Commit a plan to reserve shelter seats for its assigned trips.</p>
        ) : (
          <>
            <div className="ledger-row ledger-head">
              <span>Unit</span>
              <span>Group</span>
              <span>Shelter</span>
              <span>Seats</span>
              <span>Status</span>
            </div>
            {reserved.map((r) => (
              <div className="ledger-row" key={r.reservationId || `${r.vehicleId}-${r.incidentId}`}>
                <span>{r.vehicleId}</span>
                <span>{r.incidentId || r.groupId}</span>
                <span>{r.shelterId}</span>
                <span>{r.people}</span>
                <b>{r.status}</b>
              </div>
            ))}
          </>
        )}
      </div>
    </section>
  );
}
