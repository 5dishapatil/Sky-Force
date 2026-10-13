import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileText,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react';
import { api } from '../services/api';
import { asRecord, findMetric, formatNumber } from '../services/metricUtils';

type JsonRecord = Record<string, unknown>;

const readText = (record: JsonRecord, keys: string[]): string | null => {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  }
  return null;
};

const displayStatus = (value: string | null): string => {
  if (!value) return 'Not reported';
  return value.replace(/[_-]+/g, ' ');
};

const statusTone = (status: string | null): string => {
  const normalized = (status || '').toLowerCase();
  if (['ok', 'online', 'healthy', 'connected', 'cached', 'cached_verified', 'operational', 'available'].some((key) => normalized.includes(key))) return 'status-good';
  if (['error', 'unavailable', 'failed', 'disconnected'].some((key) => normalized.includes(key))) return 'status-bad';
  return 'status-muted';
};

const qaStages = [
  { number: '01', title: 'Schema and required fields', description: 'Check required fields and confirm values can be interpreted by the pipeline.' },
  { number: '02', title: 'Coordinate bounds', description: 'Reject or flag invalid latitude/longitude values before geospatial processing.' },
  { number: '03', title: 'Kinematic plausibility', description: 'Check speed, heading, altitude, and climb/descent values against configured limits.' },
  { number: '04', title: 'Duplicate observations', description: 'Identify repeated aircraft observations for the same timestamp.' },
  { number: '05', title: 'Missing-value handling', description: 'Retain missingness and provenance rather than silently inventing measurements.' },
  { number: '06', title: 'Anomaly isolation', description: 'Flag suspicious or inconsistent transponder and observation patterns.' },
  { number: '07', title: 'Track segmentation', description: 'Split observations into tracks when configured time gaps or continuity rules are crossed.' },
  { number: '08', title: 'Spatial and temporal aggregation', description: 'Assign observations to the documented 2° grid and 15-minute analysis windows.' },
  { number: '09', title: 'Leakage-safe data splits', description: 'Keep training, validation, and test periods chronological for evaluation.' },
];

export const DataQualityView: React.FC = () => {
  const [sources, setSources] = useState<JsonRecord[]>([]);
  const [qualitySummary, setQualitySummary] = useState<JsonRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const [sourceResult, qualityResult] = await Promise.allSettled([
      api.getDataSourcesStatus(),
      api.getDataQualitySummary(),
    ]);

    const errors: string[] = [];
    if (sourceResult.status === 'fulfilled' && Array.isArray(sourceResult.value)) {
      setSources(sourceResult.value.map(asRecord).filter((item): item is JsonRecord => item !== null));
    } else {
      setSources([]);
      errors.push(sourceResult.status === 'rejected'
        ? `Source manifest: ${sourceResult.reason instanceof Error ? sourceResult.reason.message : 'request failed'}`
        : 'Source manifest returned an unexpected payload.');
    }

    if (qualityResult.status === 'fulfilled') {
      setQualitySummary(asRecord(qualityResult.value));
    } else {
      setQualitySummary(null);
      errors.push(qualityResult.reason instanceof Error ? qualityResult.reason.message : 'Quality summary request failed.');
    }

    setError(errors.length ? errors.join(' ') : null);
    setRefreshedAt(new Date().toLocaleTimeString());
    setLoading(false);
  };

  useEffect(() => { void loadData(); }, []);

  const examined = findMetric(qualitySummary, ['records_examined', 'total_records', 'observations_processed', 'input_records', 'row_count']);
  const rejected = findMetric(qualitySummary, ['records_rejected', 'rejected_records', 'invalid_records', 'dropped_records']);
  const flagged = findMetric(qualitySummary, ['records_flagged', 'flagged_records', 'warnings_count']);
  const checkCount = findMetric(qualitySummary, ['checks_passed', 'stages_passed', 'validations_passed']);

  return (
    <div className="space-y-5 page-data-quality">
      <section className="view-hero view-hero-green">
        <div className="view-hero-copy">
          <p className="eyebrow">DATA GOVERNANCE · PROVENANCE · VALIDATION</p>
          <h2>Data &amp; quality assurance</h2>
          <p>Inspect the source manifest, distinguish synthetic from observed data, and review the validation stages that protect downstream feature engineering and model evaluation.</p>
        </div>
        <div className="view-hero-actions">
          <button type="button" className="action-secondary" onClick={() => void loadData()} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> {loading ? 'Refreshing…' : 'Refresh status'}
          </button>
        </div>
      </section>

      {error && (
        <div className="view-inline-error" role="alert">
          <AlertCircle size={16} />
          <div><strong>Some QA information could not be loaded</strong><p>{error}</p></div>
        </div>
      )}

      <section className="stats-grid qa-summary-grid" aria-label="Data quality summary">
        <article className="stat-card accent-cyan"><div className="stat-card-top"><span>Sources reported</span><Database size={17} /></div><div className="stat-card-value">{loading && sources.length === 0 ? '…' : sources.length}</div><div className="stat-card-subtitle">Returned by the source-status API</div></article>
        <article className="stat-card accent-blue"><div className="stat-card-top"><span>Records examined</span><FileText size={17} /></div><div className="stat-card-value">{formatNumber(examined, 0)}</div><div className="stat-card-subtitle">Only shown when reported by the backend</div></article>
        <article className="stat-card accent-amber"><div className="stat-card-top"><span>Rejected / invalid</span><TriangleAlert size={17} /></div><div className="stat-card-value">{formatNumber(rejected, 0)}</div><div className="stat-card-subtitle">No value is inferred when absent</div></article>
        <article className="stat-card accent-green"><div className="stat-card-top"><span>Checks passed</span><CheckCircle2 size={17} /></div><div className="stat-card-value">{checkCount === null ? '—' : formatNumber(checkCount, 0)}</div><div className="stat-card-subtitle">From the available QA summary</div></article>
      </section>

      <section className="surface-card qa-source-section">
        <div className="surface-card-heading">
          <div><p className="eyebrow">DATA SOURCE MANIFEST</p><h3>Where the data comes from</h3><p className="surface-subtitle">Each card reflects the API response. A missing source is shown as missing—not replaced with a fabricated healthy status.</p></div>
          <span className="status-tag tag-muted">{refreshedAt ? `Checked ${refreshedAt}` : 'Not checked yet'}</span>
        </div>

        {loading && sources.length === 0 ? (
          <div className="empty-state"><RefreshCw size={22} className="animate-spin"/><h3>Loading source manifest</h3><p>Waiting for the backend to return current source status.</p></div>
        ) : sources.length === 0 ? (
          <div className="empty-state"><Database size={22}/><h3>No source status returned</h3><p>Check that the FastAPI backend is running and that GET /api/data-sources/status is available.</p></div>
        ) : (
          <div className="qa-source-grid">
            {sources.map((source, index) => {
              const name = readText(source, ['source_name', 'name', 'source_key', 'source', 'kind']) || `Source ${index + 1}`;
              const status = readText(source, ['status', 'state', 'availability']);
              const provenance = readText(source, ['provenance', 'source_path', 'dataset', 'dataset_id', 'uri']);
              const details = readText(source, ['details', 'message', 'description', 'note']);
              const synthetic = source.is_synthetic === true || readText(source, ['data_kind'])?.toLowerCase() === 'synthetic';
              return (
                <article className="qa-source-card" key={`${name}-${index}`}>
                  <div className="qa-source-card-top">
                    <div className="qa-source-icon"><Database size={17}/></div>
                    <span className={`status-tag ${statusTone(status)}`}>{displayStatus(status)}</span>
                  </div>
                  <h4>{name}</h4>
                  <p>{details || 'The backend did not provide a source description.'}</p>
                  <div className="qa-source-meta"><span>DATA KIND</span><strong>{synthetic ? 'Synthetic' : readText(source, ['data_kind', 'kind']) || 'Not reported'}</strong></div>
                  <div className="qa-source-provenance"><span>PROVENANCE</span><code>{provenance || 'Not reported by API'}</code></div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="surface-card qa-pipeline-section">
        <div className="surface-card-heading">
          <div><p className="eyebrow">PREPROCESSING PIPELINE</p><h3>Nine validation stages</h3><p className="surface-subtitle">These describe the intended checks in the data pipeline; completion status is only displayed when the backend reports it.</p></div>
          <ShieldCheck size={21} className="text-emerald-300" />
        </div>
        <div className="qa-stage-grid">
          {qaStages.map((stage) => (
            <article className="qa-stage-card" key={stage.number}>
              <span className="qa-stage-number">{stage.number}</span>
              <div><h4>{stage.title}</h4><p>{stage.description}</p></div>
              <span className="qa-stage-badge">Pipeline step</span>
            </article>
          ))}
        </div>
        {qualitySummary && (
          <details className="raw-report-details">
            <summary><FileText size={15}/> Inspect raw quality summary</summary>
            <pre>{JSON.stringify(qualitySummary, null, 2)}</pre>
          </details>
        )}
        {flagged !== null && <p className="qa-footnote">Backend-reported flagged records: <strong>{formatNumber(flagged, 0)}</strong>. Review the raw summary for its exact definition.</p>}
      </section>
    </div>
  );
};
