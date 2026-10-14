import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Play,
  Layers,
  ArrowRight,
  Download,
  Database,
  RefreshCw,
  Clock,
  Sparkles,
  CloudRain,
  Link2,
  Sliders,
  Plane,
  BarChart3,
} from 'lucide-react';
import { api } from '../services/api';
import type {
  DatasetSummaryItem,
  DatasetDetailResponse,
  DatasetUploadResponse,
  RunPipelineResponse,
  DatasetType,
  LinkWeatherResponse,
} from '../types';

interface DatasetStudioViewProps {
  activeDatasetId: string;
  onSelectActiveDataset: (id: string) => void;
  onNavigate?: (tab: string) => void;
}

const DATASET_TYPE_DETAILS: Record<
  DatasetType,
  { label: string; icon: any; desc: string; required: string[]; units: string }
> = {
  aircraft_observations: {
    label: 'Flight Surveillance',
    icon: Plane,
    desc: 'Individual aircraft positions, transponder ICAO24, kinematics and altitudes',
    required: ['source_aircraft_id', 'timestamp_utc', 'latitude', 'longitude'],
    units: 'Latitude/Longitude: deg, Altitude: m, Speed: m/s, Time: UTC',
  },
  weather_observations: {
    label: 'Weather Measurements',
    icon: CloudRain,
    desc: 'Precipitation, wind speeds, gusts, and cloud cover over coordinates or grid cells',
    required: ['latitude', 'longitude', 'valid_time_utc', 'precipitation_mm'],
    units: 'Precipitation: mm/h, Wind: m/s, Cloud Cover: %, Time: UTC',
  },
  congestion_cells: {
    label: 'Pre-aggregated Congestion',
    icon: BarChart3,
    desc: 'Sector cell traffic counts and measured/predicted density scores',
    required: ['cell_id', 'aircraft_count', 'congestion_score'],
    units: 'Cell ID: alphanumeric, Aircraft Count: integer >= 0, Score: 0.0 - 1.0',
  },
};

export const DatasetStudioView: React.FC<DatasetStudioViewProps> = ({
  activeDatasetId,
  onSelectActiveDataset,
  onNavigate,
}) => {
  const [datasets, setDatasets] = useState<DatasetSummaryItem[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<DatasetDetailResponse | null>(null);
  const [uploadType, setUploadType] = useState<DatasetType>('aircraft_observations');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<DatasetUploadResponse | null>(null);
  const [runningPipeline, setRunningPipeline] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<RunPipelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [customMapping, setCustomMapping] = useState<Record<string, string>>({});

  // Weather linkage state
  const [selectedWeatherId, setSelectedWeatherId] = useState<string>('');
  const [linkingWeather, setLinkingWeather] = useState(false);
  const [linkResult, setLinkResult] = useState<LinkWeatherResponse | null>(null);

  const loadDatasets = async () => {
    try {
      const list = await api.getDatasets();
      setDatasets(list);
      const active = list.find((d) => d.id === activeDatasetId) || list[0];
      if (active) {
        const details = await api.getDataset(active.id);
        setSelectedDataset(details);
        setCustomMapping(details.schema_mapping || {});
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load datasets');
    }
  };

  useEffect(() => {
    void loadDatasets();
  }, [activeDatasetId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setUploadResult(null);
    setPipelineResult(null);
    setLinkResult(null);

    try {
      const res: DatasetUploadResponse = await api.uploadDataset(file, uploadType);
      setUploadResult(res);
      setCustomMapping(res.suggested_mapping);
      await loadDatasets();
      const details = await api.getDataset(res.dataset_id);
      setSelectedDataset(details);
      onSelectActiveDataset(res.dataset_id);
    } catch (err: any) {
      setError(err.message || 'Dataset upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleRunPipeline = async () => {
    if (!selectedDataset) return;
    setRunningPipeline(true);
    setError(null);
    try {
      const stages =
        selectedDataset.dataset_type === 'weather_observations'
          ? ['validation', 'weather_indexing']
          : ['quality', 'segmentation', 'features', 'inference'];

      const res: RunPipelineResponse = await api.runDatasetPipeline(selectedDataset.id, {
        stages,
        custom_mapping: customMapping,
      });
      setPipelineResult(res);
      const updated = await api.getDataset(selectedDataset.id);
      setSelectedDataset(updated);
      await loadDatasets();
    } catch (err: any) {
      setError(err.message || 'Pipeline execution failed');
    } finally {
      setRunningPipeline(false);
    }
  };

  const handleLinkWeather = async () => {
    if (!selectedDataset || !selectedWeatherId) return;
    setLinkingWeather(true);
    setError(null);
    setLinkResult(null);
    try {
      const res: LinkWeatherResponse = await api.linkWeather(selectedDataset.id, selectedWeatherId);
      setLinkResult(res);
      const updated = await api.getDataset(selectedDataset.id);
      setSelectedDataset(updated);
      await loadDatasets();
    } catch (err: any) {
      setError(err.message || 'Weather linking failed');
    } finally {
      setLinkingWeather(false);
    }
  };

  const handleSelectDatasetItem = async (id: string) => {
    try {
      const details = await api.getDataset(id);
      setSelectedDataset(details);
      setCustomMapping(details.schema_mapping || {});
      onSelectActiveDataset(id);
      setUploadResult(null);
      setPipelineResult(null);
      setLinkResult(null);
    } catch (err: any) {
      setError(err.message || 'Failed to switch dataset');
    }
  };

  const availableWeatherDatasets = datasets.filter((d) => d.dataset_type === 'weather_observations');

  const currentTypeMeta =
    DATASET_TYPE_DETAILS[selectedDataset?.dataset_type || uploadType] ||
    DATASET_TYPE_DETAILS['aircraft_observations'];

  return (
    <div className="space-y-6 font-mono">
      {/* Top Header Card */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-bold text-white uppercase tracking-wider">
              MULTI-SCHEMA DATASET STUDIO & LINKAGE
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Ingest and normalize aircraft tracks, geographic weather grids, and congestion matrices with isolated data provenance.
          </p>
        </div>

        {/* Dataset Selector Dropdown */}
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-400">ACTIVE DATASET:</label>
          <select
            value={selectedDataset?.id || activeDatasetId}
            onChange={(e) => handleSelectDatasetItem(e.target.value)}
            className="bg-aerospace-950 border border-aerospace-700 rounded-lg px-3 py-1.5 text-xs text-cyan-300 font-bold focus:outline-none focus:border-cyan-500"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                [{d.dataset_type?.slice(0, 7) || 'airc'}] {d.filename} ({d.row_count.toLocaleString()} rows){' '}
                {d.id === activeDatasetId ? '★ ACTIVE' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-red-950/60 border border-red-800/80 text-red-200 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Zone & Dataset Profiling Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Box with Schema Selector */}
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          <h3 className="text-xs font-bold text-white uppercase flex items-center gap-2 text-cyan-400">
            <UploadCloud className="w-4 h-4" />
            UPLOAD CSV BY SCHEMA TYPE
          </h3>

          {/* Dataset Type Selector */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-slate-400 uppercase font-semibold">1. Choose Dataset Schema:</label>
            <div className="grid grid-cols-1 gap-2">
              {(Object.keys(DATASET_TYPE_DETAILS) as DatasetType[]).map((type) => {
                const item = DATASET_TYPE_DETAILS[type];
                const Icon = item.icon;
                const isSelected = uploadType === type;
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setUploadType(type)}
                    className={`p-2.5 rounded-lg border text-left transition flex items-start gap-2.5 ${
                      isSelected
                        ? 'bg-cyan-950/80 border-cyan-500 text-cyan-200'
                        : 'bg-aerospace-950/60 border-aerospace-800 text-slate-400 hover:border-aerospace-700'
                    }`}
                  >
                    <Icon className="w-4 h-4 mt-0.5 shrink-0 text-cyan-400" />
                    <div>
                      <div className="text-xs font-bold text-white">{item.label}</div>
                      <div className="text-[10px] text-slate-400 leading-snug">{item.desc}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Upload Dropzone */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-slate-400 uppercase font-semibold">2. Select CSV File:</label>
            <label className="border-2 border-dashed border-aerospace-700 hover:border-cyan-500/80 rounded-xl p-5 flex flex-col items-center justify-center cursor-pointer bg-aerospace-950/50 hover:bg-aerospace-950 transition group">
              <UploadCloud className="w-7 h-7 text-slate-500 group-hover:text-cyan-400 transition" />
              <span className="text-xs font-semibold text-slate-300 mt-2">Browse or Drop {DATASET_TYPE_DETAILS[uploadType].label} CSV</span>
              <span className="text-[10px] text-slate-500 mt-1">{DATASET_TYPE_DETAILS[uploadType].units}</span>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                disabled={uploading}
                className="hidden"
              />
            </label>
          </div>

          {uploading && (
            <div className="text-xs text-cyan-400 flex items-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Validating schema, parsing timestamps, and storing immutable copy...</span>
            </div>
          )}

          {/* Dataset Provenance Notice */}
          <div className="p-3 rounded-lg bg-aerospace-950 border border-aerospace-800 text-[11px] text-slate-400 space-y-1">
            <div className="font-bold text-slate-300 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              PROVENANCE ISOLATION
            </div>
            <p>
              Different schema rules apply for traffic vs weather. Uploaded weather datasets can be linked to traffic datasets to replace synthetic weather in routing.
            </p>
          </div>
        </div>

        {/* Selected Dataset Details & Schema Mapping */}
        <div className="lg:col-span-2 bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex items-center justify-between border-b border-aerospace-800 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-bold text-white uppercase flex items-center gap-2 text-cyan-400">
                  <FileText className="w-4 h-4" />
                  DATASET: {selectedDataset?.filename}
                </h3>
                <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 text-[10px] font-bold">
                  {selectedDataset?.dataset_type?.toUpperCase() || 'AIRCRAFT_OBSERVATIONS'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                ID: {selectedDataset?.id} · Provenance: {selectedDataset?.provenance} · Uploaded:{' '}
                {selectedDataset?.uploaded_at_utc ? new Date(selectedDataset.uploaded_at_utc).toLocaleString() : 'N/A'}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleRunPipeline}
                disabled={runningPipeline || !selectedDataset || selectedDataset.id === 'synthetic_demo_v1'}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-aerospace-950 font-bold text-xs transition shadow-md shadow-cyan-500/20 disabled:opacity-50"
              >
                {runningPipeline ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                {runningPipeline ? 'RUNNING PIPELINE...' : 'EXECUTE PIPELINE'}
              </button>
            </div>
          </div>

          {/* Key Metrics Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-aerospace-950 border border-aerospace-800">
              <div className="text-[10px] text-slate-400 uppercase">Records</div>
              <div className="text-base font-bold text-white mt-0.5">{selectedDataset?.row_count.toLocaleString()}</div>
            </div>
            <div className="p-3 rounded-lg bg-aerospace-950 border border-aerospace-800">
              <div className="text-[10px] text-slate-400 uppercase">Columns</div>
              <div className="text-base font-bold text-white mt-0.5">{selectedDataset?.col_count}</div>
            </div>
            <div className="p-3 rounded-lg bg-aerospace-950 border border-aerospace-800">
              <div className="text-[10px] text-slate-400 uppercase">File Size</div>
              <div className="text-base font-bold text-white mt-0.5">
                {selectedDataset ? (selectedDataset.file_size_bytes / (1024 * 1024)).toFixed(2) : '0'} MB
              </div>
            </div>
            <div className="p-3 rounded-lg bg-aerospace-950 border border-aerospace-800">
              <div className="text-[10px] text-slate-400 uppercase">Pipeline Status</div>
              <div className="text-base font-bold text-emerald-400 uppercase mt-0.5">{selectedDataset?.status}</div>
            </div>
          </div>

          {/* Schema Mapping Table */}
          <div className="space-y-2">
            <div className="text-xs font-bold text-slate-300 uppercase flex items-center justify-between">
              <span>Schema Recognition ({currentTypeMeta.label}):</span>
              <span className="text-[11px] text-slate-500">Units: {currentTypeMeta.units}</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              {currentTypeMeta.required.map((canonical) => {
                const mapped = customMapping[canonical];
                return (
                  <div
                    key={canonical}
                    className={`p-2 rounded-lg border flex flex-col justify-between ${
                      mapped ? 'bg-aerospace-950 border-cyan-800/60' : 'bg-red-950/30 border-red-800/60'
                    }`}
                  >
                    <div className="text-[10px] text-slate-400 truncate" title={canonical}>
                      {canonical}
                    </div>
                    <div className="font-bold text-white truncate mt-1">
                      {mapped ? (
                        <span className="text-cyan-300 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 text-cyan-400 inline" /> {mapped}
                        </span>
                      ) : (
                        <span className="text-red-400">UNMAPPED</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Traffic and Weather Linking Section */}
          {selectedDataset?.dataset_type === 'aircraft_observations' && (
            <div className="p-4 rounded-xl bg-aerospace-950 border border-aerospace-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white flex items-center gap-1.5 text-cyan-400 uppercase">
                  <Link2 className="w-4 h-4" />
                  LINK TRAFFIC OBSERVATIONS WITH MEASURED WEATHER
                </span>
                {selectedDataset.linked_weather_dataset_id && (
                  <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300">
                    Linked to: {selectedDataset.linked_weather_dataset_id}
                  </span>
                )}
              </div>

              <p className="text-[11px] text-slate-400">
                Spatially and temporally associates flight tracks with an uploaded weather grid. Unmatched observations are marked with explicit missing-data uncertainty penalties.
              </p>

              <div className="flex flex-wrap items-center gap-3">
                <select
                  value={selectedWeatherId}
                  onChange={(e) => setSelectedWeatherId(e.target.value)}
                  className="bg-aerospace-900 border border-aerospace-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="">-- Select Measured Weather Grid --</option>
                  {availableWeatherDatasets.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.filename} ({w.row_count} records)
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  onClick={handleLinkWeather}
                  disabled={linkingWeather || !selectedWeatherId}
                  className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs transition disabled:opacity-50 flex items-center gap-1"
                >
                  {linkingWeather ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Link2 className="w-3.5 h-3.5" />}
                  <span>LINK DATASETS</span>
                </button>
              </div>

              {linkResult && (
                <div className="p-3 rounded-lg bg-cyan-950/60 border border-cyan-800 text-xs space-y-1 text-cyan-200">
                  <div className="font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                    LINKAGE COMPLETE: {linkResult.coverage_percentage}% WEATHER COVERAGE
                  </div>
                  <div>
                    Matched {linkResult.matched_rows.toLocaleString()} of {linkResult.total_traffic_rows.toLocaleString()} flight observations.
                  </div>
                  {linkResult.warnings.map((w, i) => (
                    <div key={i} className="text-amber-300 text-[11px]">
                      ⚠ {w}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Pipeline Execution Output Card */}
      {pipelineResult && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-3">
          <div className="flex items-center justify-between border-b border-aerospace-800 pb-2">
            <h3 className="text-xs font-bold text-white uppercase flex items-center gap-2 text-cyan-400">
              <CheckCircle2 className="w-4 h-4" />
              PIPELINE EXECUTION REPORT (Total: {pipelineResult.total_elapsed_seconds}s)
            </h3>
            <span className="text-xs text-emerald-400 font-bold uppercase">{pipelineResult.status}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {pipelineResult.stages.map((stage) => (
              <div key={stage.stage} className="p-3 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-cyan-300 uppercase">{stage.stage}</span>
                  <span className="text-[10px] text-slate-500">{stage.elapsed_seconds}s</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  {Object.entries(stage.output_summary).map(([k, v]) => (
                    <div key={k} className="truncate">
                      {k}: <strong className="text-white">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</strong>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
