import { useMemo, useState } from 'react';
import { AlertTriangle, Check, Languages, MapPin, Phone, ShieldAlert, SlidersHorizontal, X } from 'lucide-react';
import { api, type Snapshot } from './api';
import { CHENNAI_AREAS, depthToSeverity, type PublicArea } from './publicAreas';

type Lang = 'en' | 'ta';
type FormMode = 'rescue' | 'flood' | null;

const copy = {
  en: {
    title: 'Flood Safety Information for Chennai',
    subtitle: 'Demo data only — follow official emergency instructions during a real emergency.',
    where: 'Where are you?',
    searchPlaceholder: 'Search by area or landmark',
    useDemo: 'Use demo location',
    requestRescue: 'Request rescue',
    reportFlooding: 'Report waterlogging',
    opsDesk: 'Operations Desk',
    largeText: 'Large text',
    normalText: 'Normal text',
    plantStatus: 'Session',
    checklist: 'Safety checklist',
    disclaimer:
      'This creates a demonstration incident in the Operations Desk. It does not contact real emergency services.',
    received: 'Report received',
    beingReviewed: 'Being reviewed by operators',
    goOps: 'View in Operations Desk',
    submitAnother: 'Submit another report',
    error: 'Could not submit report. Is the API running?',
  },
  ta: {
    title: 'சென்னை வெள்ள பாதுகாப்பு தகவல்',
    subtitle: 'இது demo மட்டும் — உண்மையான அவசரத்தில் அதிகாரிகளின் அறிவுறுத்தலைப் பின்பற்றுங்கள்.',
    where: 'நீங்கள் எங்கே இருக்கிறீர்கள்?',
    searchPlaceholder: 'பகுதி அல்லது landmark தேடுங்கள்',
    useDemo: 'Demo இடம்',
    requestRescue: 'மீட்பு உதவி',
    reportFlooding: 'வெள்ள அறிக்கை',
    opsDesk: 'Operations Desk',
    largeText: 'பெரிய எழுத்து',
    normalText: 'சாதாரண எழுத்து',
    plantStatus: 'Session',
    checklist: 'பாதுகாப்பு சரிபார்ப்பு',
    disclaimer: 'இது Operations Desk-ல் demo incident உருவாக்கும். அவசர சேவைகளை தொடர்பு கொள்ளாது.',
    received: 'அறிக்கை பெறப்பட்டது',
    beingReviewed: 'ஆperator பரிசீலனை',
    goOps: 'Operations Desk-ல் பார்',
    submitAnother: 'மற்றொரு அறிக்கை',
    error: 'அறிக்கை அனுப்ப முடியவில்லை. API இயங்குகிறதா?',
  },
};

export default function PublicSafety({
  scenarioId,
  snap,
  onSwitchOps,
  onSubmitted,
}: {
  scenarioId: string;
  snap: Snapshot | null;
  onSwitchOps: () => void;
  onSubmitted: () => Promise<void>;
}) {
  const [lang, setLang] = useState<Lang>('en');
  const [largeText, setLargeText] = useState(false);
  const [selected, setSelected] = useState<PublicArea>(CHENNAI_AREAS[0]);
  const [search, setSearch] = useState('');
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [lastReport, setLastReport] = useState<{ id: string; status: string; trust: number; groupId?: string } | null>(null);

  const t = copy[lang];

  const filteredAreas = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return CHENNAI_AREAS;
    return CHENNAI_AREAS.filter(
      (a) => a.label.toLowerCase().includes(q) || a.area.toLowerCase().includes(q),
    );
  }, [search]);

  const areaReports = useMemo(() => {
    if (!snap?.groups) return 0;
    return snap.groups.filter((g) => String(g.area || '').includes(selected.area)).length;
  }, [snap, selected.area]);

  async function submitReport(form: HTMLFormElement) {
    setSubmitting(true);
    setError('');
    const data = new FormData(form);
    const people = Number(data.get('people') || 0);
    const elderly = Number(data.get('elderly') || 0);
    const children = Number(data.get('children') || 0);
    const disabled = Number(data.get('disabled') || 0);
    const medical = data.get('medical') === 'on';
    const depthM = Number(data.get('depth') || 0.45);
    const road = String(data.get('road') || 'passable');
    const description = String(data.get('description') || '').trim();
    const severity = depthToSeverity(depthM);
    const noteParts = [
      description || (formMode === 'flood' ? 'Waterlogging reported' : 'Rescue requested'),
      road !== 'passable' ? `Road: ${road}` : '',
    ].filter(Boolean);

    try {
      const result = await api.citizenReport({
        scenarioId,
        x: selected.x,
        y: selected.y,
        lat: selected.lat,
        lng: selected.lng,
        people: formMode === 'flood' && people === 0 ? 0 : Math.max(people, formMode === 'rescue' ? 1 : 0),
        elderly,
        children,
        disabled,
        medical,
        severity: road === 'blocked' ? 'impassable' : severity,
        note: noteParts.join(' · '),
        area: selected.area,
        landmark: selected.label,
        source: 'CITIZEN',
        reporter: 'public_form',
        depthCm: depthM * 100,
      });
      setLastReport({
        id: result.report.id,
        status: result.report.status,
        trust: result.report.trust,
        groupId: result.report.groupId,
      });
      setFormMode(null);
      await onSubmitted();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.error);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={`public-view ${largeText ? 'large-text' : ''}`}>
      <header className="public-header">
        <div>
          <strong>ResQFlow-Flood</strong>
          <h1>{t.title}</h1>
          <span>{t.subtitle}</span>
        </div>
        <div className="public-tools">
          <button type="button" onClick={() => setLang(lang === 'en' ? 'ta' : 'en')}>
            <Languages size={16} /> {lang === 'en' ? 'தமிழ்' : 'English'}
          </button>
          <button type="button" onClick={() => setLargeText((v) => !v)}>
            {largeText ? t.normalText : t.largeText}
          </button>
          <button type="button" onClick={onSwitchOps}>
            <SlidersHorizontal size={15} /> {t.opsDesk}
          </button>
        </div>
      </header>

      <main className="public-main">
        <section className="location-selector">
          <h2>{t.where}</h2>
          <div className="area-search">
            <input
              aria-label="Search by area or landmark"
              placeholder={t.searchPlaceholder}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button type="button" onClick={() => setSelected(CHENNAI_AREAS[0])}>
              {t.useDemo}
            </button>
          </div>
          <div className="quick-areas">
            {filteredAreas.map((area) => (
              <button
                key={area.label}
                type="button"
                className={selected.label === area.label ? 'active' : ''}
                onClick={() => setSelected(area)}
              >
                <MapPin size={14} /> {area.label}
              </button>
            ))}
          </div>
        </section>

        <section className="public-risk-card level-3">
          <div className="risk-top">
            <div>
              <small>{lang === 'ta' ? 'தற்போதைய நிலை' : 'Current safety status'}</small>
              <h2>{selected.area}</h2>
            </div>
            <span>
              Grid ({selected.x}, {selected.y}) · {areaReports} report(s) nearby
            </span>
          </div>
          <p>
            {lang === 'ta'
              ? 'இந்த பகுதியில் வெள்ளம் அல்லது மீட்பு தேவை இருந்தால் கீழே அறிக்கை அனுப்புங்கள்.'
              : 'If you see rising water or need help in this area, submit a report below. Operators review it on the same live plant.'}
          </p>
          <div className="public-action">
            <b>{lang === 'ta' ? 'இப்போது என்ன செய்ய வேண்டும்' : 'WHAT TO DO NOW'}</b>
            <span>
              {lang === 'ta'
                ? 'வெள்ள நீரில் நடக்கவோ வாகனம் ஓட்டவோ வேண்டாம். பாதுகாப்பான உயரமான இடத்திற்கு செல்லுங்கள்.'
                : 'Do not walk or drive through floodwater. Move to higher ground and keep emergency contacts ready.'}
            </span>
          </div>
        </section>

        <section className="public-actions">
          <button className="public-primary" type="button" onClick={() => setFormMode('rescue')}>
            <Phone size={17} /> {t.requestRescue}
          </button>
          <button type="button" onClick={() => setFormMode('flood')}>
            <ShieldAlert size={17} /> {t.reportFlooding}
          </button>
        </section>

        {lastReport && (
          <div className="public-confirm">
            <Check size={18} />
            <div>
              <b>{t.received.toUpperCase()}</b>
              <span>
                Reference: {lastReport.id}
                {lastReport.groupId ? ` · Group ${lastReport.groupId}` : ''}
                · {lastReport.status} · trust {lastReport.trust}
              </span>
              <small>{t.beingReviewed}. {t.disclaimer}</small>
              <div className="status-tracker">
                Report received → Being reviewed → Help assigned → Help on the way → Resolved
              </div>
              <div className="public-confirm-actions">
                <button type="button" className="public-primary" onClick={onSwitchOps}>
                  {t.goOps}
                </button>
                <button type="button" onClick={() => setLastReport(null)}>
                  {t.submitAnother}
                </button>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="public-error">
            <AlertTriangle size={16} /> {error}
          </div>
        )}

        <details className="safety-checklist">
          <summary>{t.checklist}</summary>
          <ul>
            <li>Take phone, medicines, ID, and drinking water.</li>
            <li>Help elderly people, children, and disabled persons move early.</li>
            <li>Do not walk or drive through floodwater.</li>
            <li>Avoid electric poles, open drains, and fast-moving water.</li>
            <li>Follow official emergency instructions.</li>
          </ul>
        </details>

        <p className="public-disclaimer">
          {t.plantStatus}: tick {snap?.tick ?? '—'} · reports {(snap?.reports || []).length} · open shelters{' '}
          {snap?.shelters?.filter((s) => s.open !== false).length ?? '—'}
        </p>
      </main>

      {formMode && (
        <div className="public-modal" role="dialog" aria-modal="true">
          <form
            className="public-modal-form"
            onSubmit={(e) => {
              e.preventDefault();
              void submitReport(e.currentTarget);
            }}
          >
            <button type="button" className="modal-close" onClick={() => setFormMode(null)} aria-label="Close">
              <X size={18} />
            </button>
            <h2>{formMode === 'rescue' ? t.requestRescue : t.reportFlooding}</h2>
            <p className="public-form-location">
              <MapPin size={14} /> {selected.label} · grid ({selected.x}, {selected.y})
            </p>

            <div className="public-form-grid">
              {formMode === 'rescue' && (
                <>
                  <label className="public-form-field">
                    People needing help
                    <input name="people" type="number" min={1} defaultValue={4} required />
                  </label>
                  <label className="public-form-field">
                    Elderly
                    <input name="elderly" type="number" min={0} defaultValue={0} />
                  </label>
                  <label className="public-form-field">
                    Children
                    <input name="children" type="number" min={0} defaultValue={0} />
                  </label>
                  <label className="public-form-field">
                    Disabled
                    <input name="disabled" type="number" min={0} defaultValue={0} />
                  </label>
                  <label className="public-form-field public-form-check">
                    <input name="medical" type="checkbox" />
                    Medical emergency
                  </label>
                </>
              )}

              {formMode === 'flood' && (
                <>
                  <label className="public-form-field">
                    People needing help (optional)
                    <input name="people" type="number" min={0} defaultValue={0} />
                  </label>
                  <label className="public-form-field public-form-wide">
                    Road condition
                    <select name="road" defaultValue="slow">
                      <option value="passable">Passable</option>
                      <option value="slow">Slow / risky</option>
                      <option value="unsafe">Unsafe</option>
                      <option value="blocked">Blocked</option>
                    </select>
                  </label>
                </>
              )}

              <label className="public-form-field public-form-wide">
                Water depth
                <select name="depth" defaultValue="0.45">
                  <option value="0.15">Ankle-deep (~15 cm)</option>
                  <option value="0.35">Knee-deep (~35 cm)</option>
                  <option value="0.6">Waist-deep (~60 cm)</option>
                  <option value="1.0">Chest-deep / impassable</option>
                </select>
              </label>

              <label className="public-form-field public-form-wide">
                What is happening?
                <textarea
                  name="description"
                  minLength={8}
                  required
                  placeholder="Example: Water rising near bus stop, 6 people on first floor need pickup."
                />
              </label>
            </div>

            <p className="public-form-note">{t.disclaimer}</p>
            <button className="public-primary public-form-submit" type="submit" disabled={submitting}>
              {submitting ? 'Sending…' : lang === 'ta' ? 'அனுப்பு' : 'Submit report'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
