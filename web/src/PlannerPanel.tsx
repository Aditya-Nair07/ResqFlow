import { useState } from 'react';
import { Check, RefreshCw } from 'lucide-react';
import { api, type Snapshot } from './api';

export default function PlannerPanel({
  plans,
  scenarioId,
  tick,
  snap,
  selectedGroupId,
  rankingMethod,
  onMessage,
  onPlans,
  onSelectGroup,
}: {
  plans: any | null;
  scenarioId: string;
  tick: number;
  snap: Snapshot;
  selectedGroupId?: string | null;
  rankingMethod: string;
  onMessage: (message: string) => Promise<void>;
  onPlans: (plans: any) => void;
  onSelectGroup?: (id: string) => void;
}) {
  const [selectedPlanId, setSelectedPlanId] = useState(plans?.recommendedPlanId || '');
  const [depthM, setDepthM] = useState('0.6');
  const [road, setRoad] = useState<'OPEN' | 'SLOW' | 'BLOCKED' | 'UNKNOWN'>('OPEN');
  const [peopleFound, setPeopleFound] = useState('0');
  const [peopleBoarded, setPeopleBoarded] = useState('0');
  const [vehicleStatus, setVehicleStatus] = useState('AT_SCENE');
  const [shelterId, setShelterId] = useState(snap.shelters[0]?.id || '');
  const [shelterFull, setShelterFull] = useState(false);
  const [note, setNote] = useState('');
  const [reportedBy, setReportedBy] = useState('FIELD TEAM');

  const selected = (plans?.plans || []).find((p: any) => p.planId === selectedPlanId) || (plans?.plans || [])[0];
  const openIncidents = snap.groups.filter((g) => !['RESOLVED', 'REJECTED', 'DUPLICATE', 'evacuated'].includes(g.status));
  const critical = openIncidents.filter((g) => g.severity === 'CRITICAL').length;
  const waiting = openIncidents.reduce((sum, g) => sum + (g.people - (g.evacuatedPeople || 0)), 0);
  const reserved = (snap.reservations || []).filter((r) => r.status === 'RESERVED');

  return (
    <section className="adaptive-planner">
      <div className="planner-heading">
        <div>
          <p className="eyebrow">SENSE → PRIORITIZE → GENERATE → APPROVE → RESERVE → REPLAN</p>
          <h2>Adaptive Response Planner</h2>
          <span>
            Ranking = {rankingMethod}. Plan names change objective weights only — eight checks stay on the backend.
          </span>
        </div>
        <button
          className="compute-button"
          type="button"
          onClick={async () => {
            const result = await api.comparePlans({ scenarioId, rankingMethod });
            onPlans(result);
            setSelectedPlanId(result.recommendedPlanId);
            await onMessage(result.explanation || 'Plans computed from Flood-GAPD / ranking / verify.');
          }}
        >
          <RefreshCw size={16} /> COMPUTE RESPONSE PLAN
        </button>
      </div>

      <div className="planner-metrics">
        <div><small>Open incidents</small><b>{openIncidents.length}</b></div>
        <div><small>Critical unresolved</small><b>{critical}</b></div>
        <div><small>People awaiting help</small><b>{waiting}</b></div>
        <div><small>Reserved shelter places</small><b>{reserved.reduce((s, r) => s + (r.people || 0), 0)}</b></div>
      </div>

      {plans?.plans?.length ? (
        <>
          <div className="weight-note">
            {plans.explanation}
            {' · '}Strategies: FASTEST · MAXIMUM_COVERAGE · SAFE_AND_FAIR
          </div>
          <div className="plan-table">
            <div className="plan-row plan-header">
              <span>Plan</span><span>Reached</span><span>Assign</span><span>Reserve</span><span>Left</span><span>Rejected</span><span />
            </div>
            {plans.plans.map((plan: any) => (
              <div className={`plan-row ${selected?.planId === plan.planId ? 'selected' : ''}`} key={plan.planId}>
                <b>{plan.planName}</b>
                <span>{plan.peopleReached}</span>
                <span>{plan.assignments?.length || 0}</span>
                <span>{plan.vehiclesReserved}</span>
                <span>{plan.vehiclesLeftInReserve}</span>
                <span>{plan.rejected?.length || 0}</span>
                <button type="button" onClick={() => setSelectedPlanId(plan.planId)}>Select</button>
              </div>
            ))}
          </div>
          <div className="plan-explanation">
            <b>{selected?.planName ?? 'No plan selected'}</b>
            <span>
              {(selected?.assignments || []).map((a: any) => (
                <span key={`${a.groupId}-${a.vehicleId}`}>
                  {a.groupId} → V{a.vehicleId}/{a.shelterId}
                  {a.verification ? ` (${a.verification.passed ? '8/8' : a.verification.failed?.join(',')})` : ''}
                  {' · '}
                </span>
              ))}
            </span>
            <div>
              <button
                className="approve-action"
                type="button"
                disabled={!selected}
                onClick={async () => {
                  if (!selected) return;
                  try {
                    const result = await api.approvePlan(selected.planId, {
                      scenarioId,
                      planId: selected.planId,
                      planVersion: selected.planVersion ?? plans.planVersion,
                      tick,
                      actor: 'operator',
                    });
                    await onMessage(
                      `Approved ${selected.planName}: ${result.committed?.length || 0} committed, ${result.rejected?.length || 0} rejected`,
                    );
                    onPlans(null);
                  } catch (err) {
                    await onMessage(`Approve failed: ${err instanceof Error ? err.message : String(err)}`);
                  }
                }}
              >
                <Check size={14} /> Approve selected plan
              </button>
            </div>
          </div>
          {selected?.rejected?.length ? (
            <div className="planner-warning">
              NO SAFE PLAN for: {selected.rejected.map((r: any) => r.groupId).join(', ')} — HUMAN ESCALATION REQUIRED.
            </div>
          ) : null}
        </>
      ) : (
        <div className="weight-note">Compute a response plan to compare FASTEST / MAXIMUM_COVERAGE / SAFE_AND_FAIR on the live plant.</div>
      )}

      {reserved.length > 0 && (
        <div className="ledger">
          <div className="planner-subheading">
            <b>RESOURCE RESERVATION LEDGER</b>
            <span>{reserved.length} active</span>
          </div>
          {reserved.map((r) => (
            <div className="ledger-row" key={r.reservationId}>
              <span>{r.vehicleId}</span>
              <span>{r.incidentId}</span>
              <span>{r.shelterId}</span>
              <span>{r.people} places</span>
              <b>{r.status}</b>
            </div>
          ))}
        </div>
      )}

      <div className="field-update">
        <div className="planner-subheading">
          <b>FIELD UPDATE / REPLANNING</b>
          <span>High-trust feedback updates the same plant used by dispatch. Unsafe routes pause.</span>
        </div>
        <div className="field-form">
          <label>
            Target group
            <select
              value={selectedGroupId || snap.groups[0]?.id || ''}
              onChange={(e) => onSelectGroup?.(e.target.value)}
            >
              {(snap.groups || []).map((g) => (
                <option key={g.id} value={g.id}>{g.id} · {g.label || g.area}</option>
              ))}
            </select>
          </label>
          <label>
            Observed depth (m)
            <input type="number" step="0.05" value={depthM} onChange={(e) => setDepthM(e.target.value)} />
          </label>
          <label>
            Road status
            <select value={road} onChange={(e) => setRoad(e.target.value as typeof road)}>
              <option>OPEN</option>
              <option>SLOW</option>
              <option>BLOCKED</option>
              <option>UNKNOWN</option>
            </select>
          </label>
          <label>
            People found
            <input type="number" value={peopleFound} onChange={(e) => setPeopleFound(e.target.value)} />
          </label>
          <label>
            People boarded
            <input type="number" value={peopleBoarded} onChange={(e) => setPeopleBoarded(e.target.value)} />
          </label>
          <label>
            Vehicle status
            <select value={vehicleStatus} onChange={(e) => setVehicleStatus(e.target.value)}>
              <option>AT_SCENE</option>
              <option>EN_ROUTE</option>
              <option>BLOCKED</option>
              <option>BROKEN</option>
              <option>OUT_OF_SERVICE</option>
            </select>
          </label>
          <label>
            Shelter
            <select value={shelterId} onChange={(e) => setShelterId(e.target.value)}>
              {snap.shelters.map((s) => (
                <option key={s.id} value={s.id}>{s.label || s.id}</option>
              ))}
            </select>
          </label>
          <label className="toggle-field">
            <input type="checkbox" checked={shelterFull} onChange={(e) => setShelterFull(e.target.checked)} />
            Shelter full
          </label>
          <label>
            Reported by
            <input value={reportedBy} onChange={(e) => setReportedBy(e.target.value)} />
          </label>
          <label>
            Note
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Field observation" />
          </label>
          <button
            type="button"
            onClick={async () => {
              const groupId = selectedGroupId || snap.groups[0]?.id;
              const vehicleId = snap.groups.find((g) => g.id === groupId)?.assignedVehicleId
                || snap.vehicles.find((v) => v.status === 'busy')?.id;
              const result = await api.fieldUpdate({
                scenarioId,
                groupId,
                actor: reportedBy || 'FIELD TEAM',
                source: 'FIELD_TEAM',
                observedDepthCm: Number(depthM) * 100,
                roadStatus: road,
                peopleFound: Number(peopleFound) || undefined,
                peopleBoarded: Number(peopleBoarded) || undefined,
                vehicleId: vehicleStatus === 'AT_SCENE' || vehicleStatus === 'EN_ROUTE' ? undefined : vehicleId,
                vehicleStatus: vehicleStatus === 'AT_SCENE' || vehicleStatus === 'EN_ROUTE' ? undefined : vehicleStatus,
                shelterId: shelterFull ? shelterId : undefined,
                shelterFull: shelterFull || undefined,
                note,
              });
              await onMessage(
                result.update?.replanRequired
                  ? `Field update applied — REPLAN REQUIRED (${road}, ${depthM}m)`
                  : `Field update applied (${road}, ${depthM}m)`,
              );
            }}
          >
            Submit Field Update
          </button>
          <button
            className="replan-button"
            type="button"
            onClick={async () => {
              await api.replan({ scenarioId, rankingMethod, closedLoop: true });
              await onMessage('Replan tick executed after field feedback.');
            }}
          >
            Replan
          </button>
        </div>
        {(snap.fieldUpdates || []).slice(-3).reverse().map((fu) => (
          <div className="forecast-row" key={fu.id}>
            <b>{fu.id}</b>
            <span>{fu.note || fu.effects?.roadClosed || 'update'} · trust {fu.trust}</span>
            <small>{fu.replanRequired ? 'REPLAN REQUIRED' : 'recorded'} · {fu.actor}</small>
          </div>
        ))}
      </div>
    </section>
  );
}
