import { useState } from 'react';
import { api, type Snapshot } from './api';

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
  const [lang, setLang] = useState<'en' | 'ta'>('en');
  const [largeText, setLargeText] = useState(false);
  const [x, setX] = useState(12);
  const [y, setY] = useState(10);
  const [people, setPeople] = useState(6);
  const [elderly, setElderly] = useState(1);
  const [children, setChildren] = useState(1);
  const [severity, setSeverity] = useState('rising');
  const [area, setArea] = useState('Velachery');
  const [note, setNote] = useState('');
  const [status, setStatus] = useState('');

  const copy = lang === 'ta'
    ? {
        title: 'பொது பாதுகாப்பு பார்வை',
        report: 'நீர் தேங்குதல் / மீட்பு அறிக்கை',
        submit: 'அனுப்பு',
        disclaimer: 'இது அவசர சேவைகளுடன் இணைக்கப்படவில்லை. முடிவு ஆதரவு முன்மாதிரி மட்டுமே.',
      }
    : {
        title: 'Public Safety View',
        report: 'Waterlogging / rescue report',
        submit: 'Submit report',
        disclaimer: 'Not connected to emergency services. Decision-support prototype only.',
      };

  return (
    <div className={`public-view ${largeText ? 'large-text' : ''}`}>
      <header className="public-header">
        <div>
          <strong>ResQFlow-Flood</strong>
          <h1>{copy.title}</h1>
          <span>{copy.disclaimer}</span>
        </div>
        <div className="public-tools">
          <button type="button" onClick={() => setLang(lang === 'en' ? 'ta' : 'en')}>{lang === 'en' ? 'தமிழ்' : 'English'}</button>
          <button type="button" onClick={() => setLargeText((v) => !v)}>{largeText ? 'Normal text' : 'Large text'}</button>
          <button type="button" onClick={onSwitchOps}>Operations Desk</button>
        </div>
      </header>
      <main className="public-main">
        <form
          className="public-risk-card"
          onSubmit={async (e) => {
            e.preventDefault();
            const result = await api.citizenReport({
              scenarioId,
              x,
              y,
              people,
              elderly,
              children,
              severity,
              note,
              area,
              source: 'CITIZEN',
              reporter: 'public_form',
            });
            setStatus(`Report ${result.report.id} · ${result.report.status} · trust ${result.report.trust}`);
            await onSubmitted();
          }}
        >
          <h2>{copy.report}</h2>
          <label>Area / landmark<input value={area} onChange={(e) => setArea(e.target.value)} /></label>
          <label>Grid X<input type="number" value={x} onChange={(e) => setX(Number(e.target.value))} min={0} max={24} /></label>
          <label>Grid Y<input type="number" value={y} onChange={(e) => setY(Number(e.target.value))} min={0} max={24} /></label>
          <label>People needing help<input type="number" value={people} onChange={(e) => setPeople(Number(e.target.value))} min={0} /></label>
          <label>Elderly<input type="number" value={elderly} onChange={(e) => setElderly(Number(e.target.value))} min={0} /></label>
          <label>Children<input type="number" value={children} onChange={(e) => setChildren(Number(e.target.value))} min={0} /></label>
          <label>
            Water severity
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="shallow">Shallow</option>
              <option value="rising">Rising</option>
              <option value="knee_deep">Knee deep</option>
              <option value="impassable">Impassable</option>
            </select>
          </label>
          <label>Description<textarea value={note} onChange={(e) => setNote(e.target.value)} /></label>
          <button className="public-primary" type="submit">{copy.submit}</button>
          {status && <div className="status-tracker">{status}</div>}
        </form>
        <p className="public-disclaimer">
          Plant tick {snap?.tick ?? '—'} · reports in session {(snap?.reports || []).length} · open shelters {snap?.shelters.filter((s) => s.open !== false).length ?? '—'}
        </p>
      </main>
    </div>
  );
}
