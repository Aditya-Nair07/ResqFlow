import { useEffect, useState } from 'react';
import { Check, RefreshCw } from 'lucide-react';
import { api, type Snapshot } from './api';

/**
 * Operator commit path: Compare → Select → Approve → Ledger.
 * Crew feedback lives on Operations desk — keep this panel focused.
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
  const [selectedPlanId, setSelectedPlanId] = useState(plans?.recommendedPlanId || '');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (plans?.recommendedPlanId) setSelectedPlanId(plans.recommendedPlanId);
  }, [plans?.recommendedPlanId]);

  const selected = (plans?.plans || []).find((p: any) => p.planId === selectedPlanId) || (plans?.plans || [])[0];
  const waiting = snap.groups
    .filter((g) => !['RESOLVED', 'REJECTED', 'DUPLICATE', 'evacuated'].includes(g.status))
    .reduce((sum, g) => sum + Math.max(0, (g.people || 0) - (g.evacuatedPeople || 0)), 0);
  const freeUnits = (snap.vehicles || []).filter((v) => v.status === 'available').length;
  const reserved = (snap.reservations || []).filter((r) => r.status === 'RESERVED');

  async function compute() {
    setBusy(true);
    try {
      const result = await api.comparePlans({ scenarioId, rankingMethod });
      onPlans(result);
      setSelectedPlanId(result.recommendedPlanId);
      await onMessage(result.explanation || 'Plans compared — pick one and Approve.');
    } catch (err) {
      await onMessage(`Compare failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!selected || !plans) return;
    setBusy(true);
    try {
      const result = await api.approvePlan(selected.planId, {
        scenarioId,
        planId: selected.planId,
        planVersion: selected.planVersion ?? plans.planVersion,
        tick,
        actor: 'operator',
      });
      await onRefresh();
      await onMessage(
        `Approved ${selected.planName}: ${result.committed?.length || 0} committed`
          + (result.rejected?.length ? `, ${result.rejected.length} rejected` : '')
          + '. Check the ledger and map.',
      );
      onPlans(null);
    } catch (err) {
      await onMessage(`Approve failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  }

  async function replan() {
    setBusy(true);
    try {
      await api.replan({ scenarioId, rankingMethod, closedLoop: true });
      await onRefresh();
      await onMessage('Replan tick done — free units may pick up leftovers.');
    } catch (err) {
      await onMessage(`Replan failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="adaptive-planner review-planner">
      <div className="planner-heading">
        <div>
          <p className="eyebrow">OPERATOR COMMIT</p>
          <h2>Response planner</h2>
          <span>
            Compare three strategies, approve one. Pause Run first so free units stay available.
            Ranking = {rankingMethod}.
          </span>
        </div>
        <button className="compute-button" type="button" disabled={busy} onClick={() => void compute()}>
          <RefreshCw size={16} /> Compute plans
        </button>
      </div>

      <div className="planner-metrics slim">
        <div><small>Still waiting</small><b>{waiting}</b></div>
        <div><small>Free units</small><b>{freeUnits}</b></div>
        <div><small>Reserved seats</small><b>{reserved.reduce((s, r) => s + (r.people || 0), 0)}</b></div>
      </div>

      {plans?.plans?.length ? (
        <>
          <div className="weight-note">{plans.explanation}</div>
          <div className="plan-table">
            <div className="plan-row plan-header">
              <span>Plan</span>
              <span>People</span>
              <span>Assign</span>
              <span>Left</span>
              <span>Rejected</span>
              <span />
            </div>
            {plans.plans.map((plan: any) => (
              <div
                className={`plan-row ${selected?.planId === plan.planId ? 'selected' : ''}`}
                key={plan.planId}
              >
                <b>{plan.planName}</b>
                <span>{plan.peopleReached}</span>
                <span>{plan.assignments?.length || 0}</span>
                <span>{plan.vehiclesLeftInReserve}</span>
                <span>{plan.rejected?.length || 0}</span>
                <button type="button" onClick={() => setSelectedPlanId(plan.planId)}>Select</button>
              </div>
            ))}
          </div>

          <div className="plan-explanation">
            <b>{selected?.planName ?? 'No plan selected'}</b>
            <span>
              {(selected?.assignments || []).length
                ? (selected.assignments || []).map((a: any) => (
                  <span key={`${a.groupId}-${a.vehicleId}`}>
                    {a.groupId} → unit {a.vehicleId} / {a.shelterId}
                    {a.verification ? ` (${a.verification.passed ? '8/8' : (a.verification.failed || []).join(',')})` : ''}
                    {' · '}
                  </span>
                ))
                : 'No assignments in this plan.'}
            </span>
            <div className="planner-actions">
              <button
                className="approve-action"
                type="button"
                disabled={!selected || busy || !(selected.assignments || []).length}
                onClick={() => void approve()}
              >
                <Check size={14} /> Approve selected plan
              </button>
              <button className="replan-button" type="button" disabled={busy} onClick={() => void replan()}>
                Replan tick
              </button>
            </div>
          </div>

          {selected?.rejected?.length ? (
            <div className="planner-warning">
              No safe assignment for: {selected.rejected.map((r: any) => r.groupId).join(', ')}.
            </div>
          ) : null}
        </>
      ) : (
        <div className="weight-note">
          Compute to compare FASTEST · MAXIMUM COVERAGE · SAFE AND FAIR on the live plant.
        </div>
      )}

      <div className="ledger">
        <div className="planner-subheading">
          <b>RESERVATION LEDGER</b>
          <span>{reserved.length ? `${reserved.length} active` : 'None active'}</span>
        </div>
        {reserved.length === 0 ? (
          <p className="planner-empty">Approve a plan to reserve shelter seats for assigned trips.</p>
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
