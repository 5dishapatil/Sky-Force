import React, { useState, useEffect } from 'react';
import {
  Database,
  Table,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
  Download,
  Filter,
  RefreshCw,
  Search,
} from 'lucide-react';
import { api } from '../services/api';
import type {
  DatasetDetailResponse,
  DatasetRawPreviewResponse,
  DatasetSummaryItem,
} from '../types';

interface DatasetExplorerViewProps {
  activeDatasetId: string;
}

export const DatasetExplorerView: React.FC<DatasetExplorerViewProps> = ({
  activeDatasetId,
}) => {
  const [datasets, setDatasets] = useState<DatasetSummaryItem[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [datasetDetail, setDatasetDetail] =
    useState<DatasetDetailResponse | null>(null);
  const [rawPreview, setRawPreview] =
    useState<DatasetRawPreviewResponse | null>(null);

  const [activeTab, setActiveTab] = useState<string>('raw');
  const [page, setPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [listLoading, setListLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');

  // Load the dataset list independently of detail and preview requests.
  useEffect(() => {
    let cancelled = false;

    const loadDatasets = async () => {
      setListLoading(true);
      setError(null);

      try {
        const list = await api.getDatasets();

        if (cancelled) return;

        const availableDatasets = Array.isArray(list) ? list : [];
        setDatasets(availableDatasets);

        if (availableDatasets.length === 0) {
          setSelectedDatasetId('');
          setDatasetDetail(null);
          setRawPreview(null);
          return;
        }

        // Prefer the active dataset, then the current selection, then the first.
        const nextDataset =
          availableDatasets.find((d) => d.id === activeDatasetId) ??
          availableDatasets.find((d) => d.id === selectedDatasetId) ??
          availableDatasets[0];

        setSelectedDatasetId(nextDataset.id);
      } catch (err: unknown) {
        if (cancelled) return;

        const message =
          err instanceof Error ? err.message : 'Unknown API error';

        setError(`Could not load dataset list: ${message}`);
        setDatasets([]);
        setSelectedDatasetId('');
      } finally {
        if (!cancelled) setListLoading(false);
      }
    };

    void loadDatasets();

    return () => {
      cancelled = true;
    };
  }, [activeDatasetId]);

  // Load details and preview only after a valid dataset has been selected.
  useEffect(() => {
    if (!selectedDatasetId) {
      setDatasetDetail(null);
      setRawPreview(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const loadSelectedDataset = async () => {
      setLoading(true);
      setError(null);
      setDatasetDetail(null);
      setRawPreview(null);

      try {
        const detail = await api.getDataset(selectedDatasetId);

        if (cancelled) return;
        setDatasetDetail(detail);

        try {
          const preview = await api.getDatasetPreview(
            selectedDatasetId,
            page,
            40
          );

          if (!cancelled) setRawPreview(preview);
        } catch (previewErr: unknown) {
          if (cancelled) return;

          const message =
            previewErr instanceof Error
              ? previewErr.message
              : 'Unknown preview error';

          setError(`Dataset loaded, but preview failed: ${message}`);
        }
      } catch (detailErr: unknown) {
        if (cancelled) return;

        const message =
          detailErr instanceof Error
            ? detailErr.message
            : 'Unknown dataset error';

        setError(`Could not load dataset details: ${message}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void loadSelectedDataset();

    return () => {
      cancelled = true;
    };
  }, [selectedDatasetId, page]);

  const filteredRows =
    rawPreview?.rows?.filter((row) => {
      if (!searchFilter.trim()) return true;

      return Object.values(row).some((value) =>
        String(value ?? '')
          .toLowerCase()
          .includes(searchFilter.toLowerCase())
      );
    }) ?? [];

  return (
    <div className="space-y-6 font-mono">
      {/* Top Bar */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-bold text-white uppercase tracking-wider">DATASET LIFECYCLE EXPLORER</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Examine every transformation stage: raw inputs, QA filtering, inferred tracks, feature frames, and model inferences.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label
            htmlFor="dataset-explorer-select"
            className="text-xs text-slate-400"
          >
            INSPECTING DATASET:
          </label>

          <select
            id="dataset-explorer-select"
            value={selectedDatasetId}
            disabled={listLoading || datasets.length === 0}
            onChange={(e) => {
              setSelectedDatasetId(e.target.value);
              setPage(1);
              setSearchFilter('');
            }}
            className="min-w-[220px] bg-aerospace-950 border border-aerospace-700 rounded-lg px-3 py-1.5 text-xs text-cyan-300 font-bold focus:outline-none focus:border-cyan-500 disabled:opacity-60"
          >
            {listLoading && <option value="">Loading datasets...</option>}

            {!listLoading && datasets.length === 0 && (
              <option value="">No datasets available</option>
            )}

            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.filename} ({dataset.row_count.toLocaleString()} rows)
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => {
              // Re-fetch the list by refreshing the page.
              window.location.reload();
            }}
            className="px-3 py-1.5 text-xs rounded-lg border border-aerospace-700 text-slate-300 hover:border-cyan-500"
          >
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-red-950/60 border border-red-800/80 text-red-200 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Tabs Bar */}
      <div className="flex flex-wrap gap-2 border-b border-aerospace-800 pb-2 text-xs">
        {[
          { id: 'raw', label: '1. Raw Observations' },
          { id: 'qa', label: '2. Quality & Anomaly Report' },
          { id: 'features', label: '3. Feature Matrix (21 Congestion / 12 ETA)' },
          { id: 'inferences', label: '4. Model Inferences & OOD' },
          { id: 'runs', label: '5. Pipeline Execution Log' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3.5 py-2 rounded-lg font-bold transition flex items-center gap-2 ${
              activeTab === tab.id
                ? 'bg-cyan-500/15 border border-cyan-500 text-cyan-300 shadow-md shadow-cyan-950'
                : 'bg-aerospace-900 border border-aerospace-800 text-slate-400 hover:text-slate-200 hover:border-aerospace-700'
            }`}
          >
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab 1: Raw Observations Preview */}
      {activeTab === 'raw' && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          
          {loading && (
            <div className="py-8 text-center text-xs text-cyan-300">
              Loading dataset preview...
            </div>
          )}

          {!listLoading && datasets.length === 0 && (
            <div className="py-8 text-center text-sm text-slate-400">
              No registered datasets found. Upload a dataset in Dataset Studio first.
            </div>
          )}

          {!loading && selectedDatasetId && rawPreview && (
            <div className="text-xs text-slate-400">
              Preview loaded: {rawPreview.total_rows.toLocaleString()} total rows
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Table className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-white uppercase">Raw CSV Inspection Table</span>
              <span className="text-[11px] text-slate-400">
                (Showing {filteredRows.length} of {rawPreview?.total_rows?.toLocaleString() || 0} rows)
              </span>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
                <input
                  type="text"
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  placeholder="Filter table rows..."
                  className="bg-aerospace-950 border border-aerospace-700 rounded-lg pl-8 pr-3 py-1 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Pagination Controls */}
              <div className="flex items-center gap-1.5 text-xs text-slate-300">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  className="px-2 py-1 rounded bg-aerospace-950 border border-aerospace-800 hover:border-aerospace-700 disabled:opacity-40"
                >
                  Prev
                </button>
                <span className="px-2">Page {page}</span>
                <button
                  disabled={!rawPreview || page * rawPreview.page_size >= rawPreview.total_rows}
                  onClick={() => setPage(page + 1)}
                  className="px-2 py-1 rounded bg-aerospace-950 border border-aerospace-800 hover:border-aerospace-700 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-aerospace-800">
            <table className="w-full text-left text-[11px] divide-y divide-aerospace-800">
              <thead className="bg-aerospace-950 text-slate-400 uppercase">
                <tr>
                  {rawPreview?.columns?.map((col) => (
                    <th key={col} className="py-2.5 px-3 font-semibold whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-aerospace-800 bg-aerospace-900/60 text-slate-300">
                {filteredRows.map((row, i) => (
                  <tr key={i} className="hover:bg-aerospace-850/60 transition">
                    {rawPreview?.columns?.map((col) => (
                      <td key={col} className="py-2 px-3 whitespace-nowrap">
                        {row[col] !== null && row[col] !== undefined ? String(row[col]) : <span className="text-slate-600">null</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Quality & Anomaly Report */}
      {activeTab === 'qa' && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex items-center gap-2 text-cyan-400 font-bold text-xs uppercase border-b border-aerospace-800 pb-3">
            <CheckCircle2 className="w-4 h-4" />
            DATA QUALITY & ANOMALY FILTERING REPORT
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-aerospace-950 border border-aerospace-800 space-y-2">
              <div className="text-xs font-bold text-slate-300 uppercase">Excluded Anomalies</div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Records with physical coordinate errors outside [-90, +90] / [-180, +180], unparseable timestamps, or exact duplicate reports are removed.
              </p>
              <div className="pt-2 text-xs text-white">
                <div>Invalid Coords: <strong className="text-rose-400">Excluded</strong></div>
                <div>Duplicates: <strong className="text-rose-400">Deduplicated</strong></div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-aerospace-950 border border-aerospace-800 space-y-2">
              <div className="text-xs font-bold text-slate-300 uppercase">Flagged Plausibility Bounds</div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Ground speeds &gt; 350 m/s (~680 kt) or altitudes outside [-500m, 16000m] are flagged and set to NaN rather than deleted, preserving flight continuity.
              </p>
              <div className="pt-2 text-xs text-white">
                <div>Implausible Speeds: <strong className="text-amber-400">Flagged & Set NaN</strong></div>
                <div>Position Jumps: <strong className="text-amber-400">Isolated & Pruned</strong></div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-aerospace-950 border border-aerospace-800 space-y-2">
              <div className="text-xs font-bold text-slate-300 uppercase">Missingness Policy</div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Unknown altitudes and weather observations are never imputed with zeroes. Unknown values elevate the data uncertainty component.
              </p>
              <div className="pt-2 text-xs text-white">
                <div>Missing Altitude: <strong className="text-purple-400">Kept NaN (No Impute)</strong></div>
                <div>Unobserved Weather: <strong className="text-purple-400">Uncertainty Raised (+0.4)</strong></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Feature Matrix */}
      {activeTab === 'features' && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex items-center justify-between border-b border-aerospace-800 pb-3">
            <div>
              <div className="flex items-center gap-2 text-cyan-400 font-bold text-xs uppercase">
                <Layers className="w-4 h-4" />
                ACTIVE MODEL FEATURE DICTIONARY
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Engineered features aligned with the active RandomForest model schemas in the registry.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Congestion Feature Family */}
            <div className="p-4 rounded-xl bg-aerospace-950 border border-aerospace-800 space-y-3">
              <div className="text-xs font-bold text-cyan-300 uppercase">
                Congestion Classifier Features (21 Fields):
              </div>
              <div className="flex flex-wrap gap-1.5 text-[11px]">
                {[
                  'cell_id', 'aircraft_count', 'count_lag1', 'count_lag2', 'count_lag4',
                  'count_roll4_mean', 'traffic_change', 'neighbor_count', 'neighbor_count_lag1',
                  'mean_speed_mps', 'speed_std_mps', 'mean_altitude_m', 'hour_sin', 'hour_cos',
                  'wind_speed_10m_ms', 'wind_dir_sin', 'wind_dir_cos', 'precipitation_mm',
                  'cloud_cover_pct', 'wind_gusts_10m_ms', 'weather_missing',
                ].map((f) => (
                  <span key={f} className="px-2 py-0.5 rounded bg-aerospace-900 border border-aerospace-800 text-slate-300">
                    {f}
                  </span>
                ))}
              </div>
            </div>

            {/* ETA Feature Family */}
            <div className="p-4 rounded-xl bg-aerospace-950 border border-aerospace-800 space-y-3">
              <div className="text-xs font-bold text-cyan-300 uppercase">
                ETA Regressor Features (12 Fields):
              </div>
              <div className="flex flex-wrap gap-1.5 text-[11px]">
                {[
                  'segment_distance_km', 'bearing_sin', 'bearing_cos', 'hour_sin', 'hour_cos',
                  'from_airport', 'to_airport', 'entry_speed_mps', 'entry_altitude_m',
                  'tailwind_proxy_ms', 'weather_severity', 'corridor_count_prev_window',
                ].map((f) => (
                  <span key={f} className="px-2 py-0.5 rounded bg-aerospace-900 border border-aerospace-800 text-slate-300">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Model Inferences & OOD */}
      {activeTab === 'inferences' && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex items-center gap-2 text-cyan-400 font-bold text-xs uppercase border-b border-aerospace-800 pb-3">
            <Sparkles className="w-4 h-4" />
            ML INFERENCE & OUT-OF-DISTRIBUTION (OOD) VALIDATION
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            Inferences are produced using active version-locked RandomForest models verified via SHA-256 checksums.
            Observations outside the training 1st-to-99th percentiles are explicitly flagged with OOD warnings, raising edge uncertainty.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800">
              <div className="text-[10px] text-slate-400 uppercase">Congestion Classes</div>
              <div className="text-sm font-bold text-white mt-1">LOW (≤2), MEDIUM (3-4), HIGH (≥5)</div>
            </div>
            <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800">
              <div className="text-[10px] text-slate-400 uppercase">Target Window</div>
              <div className="text-sm font-bold text-cyan-300 mt-1">Next 15-Minute Window</div>
            </div>
            <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800">
              <div className="text-[10px] text-slate-400 uppercase">Target Leakage Policy</div>
              <div className="text-sm font-bold text-emerald-400 mt-1">Zero Leakage (Strict Floor Split)</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Pipeline Runs Log */}
      {activeTab === 'runs' && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="text-xs font-bold text-white uppercase border-b border-aerospace-800 pb-3">
            Execution Audit History
          </div>

          <div className="space-y-2">
            {datasetDetail?.pipeline_runs?.map((run, i) => (
              <div key={i} className="p-3 rounded-lg bg-aerospace-950 border border-aerospace-800 text-xs flex items-center justify-between">
                <div>
                  <span className="font-bold text-cyan-300 uppercase">{run.stage}</span>
                  <span className="text-slate-500 ml-2">Duration: {run.elapsed_seconds}s</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-bold uppercase">
                  {run.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};