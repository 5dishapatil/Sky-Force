import React, { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  CloudRain,
  Info,
  RadioTower,
  RotateCcw,
  ShieldAlert,
  Wind,
  Zap,
} from 'lucide-react';
import type { Airport, AirspaceNetwork, Scenario, RouteDetail } from '../types';
import { AirspaceMap } from '../components/AirspaceMap';

// Props are kept compatible with the existing parent component. This view is
// intentionally a self-contained presentation demo and does not call the API
// or use backend-provided scenario/network data.
interface ScenarioStudioViewProps {
  scenarios: Scenario[];
  onScenarioChange: () => void;
  airports: Airport[];
  network: AirspaceNetwork | null;
}

type DemoScenario = {
  id: string;
  name: string;
  shortName: string;
  description: string;
  eventLabel: string;
  status: string;
  severity: 'NOMINAL' | 'MODERATE' | 'HIGH';
  icon: React.ComponentType<{ className?: string }>;
  distanceKm: number;
  etaMin: number;
  weatherExposureKm: number;
  congestionExposureKm: number;
  uncertainty: number;
  score: number;
  hops: number;
  geometry: [number, number][];
  path: string[];
  explanation: string[];
};

const BASELINE_GEOMETRY: [number, number][] = [
  [28.5562, 77.1000], // Delhi
  [26.8242, 75.8122], // Jaipur
  [23.0772, 72.6347], // Ahmedabad
  [19.0896, 72.8656], // Mumbai
];

const DEMO_AIRPORTS: Airport[] = [
  { node_id: 'VIDP', icao: 'VIDP', iata: 'DEL', name: 'Indira Gandhi International Airport', latitude: 28.5562, longitude: 77.1000, country: 'India', source: 'static-demo' },
  { node_id: 'JAI', icao: 'VIJP', iata: 'JAI', name: 'Jaipur International Airport', latitude: 26.8242, longitude: 75.8122, country: 'India', source: 'static-demo' },
  { node_id: 'AMD', icao: 'VAAH', iata: 'AMD', name: 'Sardar Vallabhbhai Patel International Airport', latitude: 23.0772, longitude: 72.6347, country: 'India', source: 'static-demo' },
  { node_id: 'VABB', icao: 'VABB', iata: 'BOM', name: 'Chhatrapati Shivaji Maharaj International Airport', latitude: 19.0896, longitude: 72.8656, country: 'India', source: 'static-demo' },
  { node_id: 'BHO', icao: 'VABP', iata: 'BHO', name: 'Raja Bhoj Airport', latitude: 23.2875, longitude: 77.3374, country: 'India', source: 'static-demo' },
  { node_id: 'PNQ', icao: 'VAPO', iata: 'PNQ', name: 'Pune Airport', latitude: 18.5822, longitude: 73.9197, country: 'India', source: 'static-demo' },
  { node_id: 'IDR', icao: 'VAID', iata: 'IDR', name: 'Devi Ahilya Bai Holkar Airport', latitude: 22.7218, longitude: 75.8011, country: 'India', source: 'static-demo' },
  { node_id: 'STV', icao: 'VASU', iata: 'STV', name: 'Surat Airport', latitude: 21.1141, longitude: 72.7411, country: 'India', source: 'static-demo' },
  { node_id: 'UDR', icao: 'VAUD', iata: 'UDR', name: 'Maharana Pratap Airport', latitude: 24.6177, longitude: 73.8961, country: 'India', source: 'static-demo' },
  { node_id: 'LKO', icao: 'VILK', iata: 'LKO', name: 'Chaudhary Charan Singh International Airport', latitude: 26.7606, longitude: 80.8893, country: 'India', source: 'static-demo' },
];

const BASELINE_ROUTE: RouteDetail = {
  found: true,
  label: 'Baseline route · normal operations',
  algorithm: 'static-demo',
  path: ['VIDP', 'JAI', 'AMD', 'VABB'],
  geometry: BASELINE_GEOMETRY,
  totals: {
    distance_km: 1185,
    estimated_time_min: 108,
    weather_exposure_km: 110,
    congestion_exposure_km: 145,
    mean_uncertainty: 0.12,
    composite_score: 1.0,
    hops: 3,
    closed_edges_in_route: 0,
  },
  explanation: ['Illustrative baseline path used for this static presentation demo.'],
};

const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'normal',
    name: 'Normal Operations',
    shortName: 'Baseline',
    description: 'Reference conditions with no disruption.',
    eventLabel: 'No active disruption',
    status: 'REFERENCE ROUTE',
    severity: 'NOMINAL',
    icon: CheckCircle2,
    distanceKm: 1185,
    etaMin: 108,
    weatherExposureKm: 110,
    congestionExposureKm: 145,
    uncertainty: 0.12,
    score: 1.0,
    hops: 3,
    geometry: BASELINE_GEOMETRY,
    path: ['VIDP', 'JAI', 'AMD', 'VABB'],
    explanation: [
      'No disruption is active in this scenario, so the baseline corridor remains the preferred illustrative route.',
      'The path travels from Delhi through the Jaipur and Ahmedabad sectors before reaching Mumbai.',
      'This reference is used to compare the additional distance and time in the other scenarios.',
    ],
  },
  {
    id: 'closure',
    name: 'Restricted Airspace Sector',
    shortName: 'Sector closure',
    description: 'A temporary restricted sector blocks part of the western corridor.',
    eventLabel: 'Airspace restriction',
    status: 'ROUTE DEVIATION',
    severity: 'HIGH',
    icon: ShieldAlert,
    distanceKm: 1295,
    etaMin: 119,
    weatherExposureKm: 105,
    congestionExposureKm: 120,
    uncertainty: 0.14,
    score: 1.09,
    hops: 3,
    geometry: [
      [28.5562, 77.1000],
      [26.0, 78.1],
      [23.2875, 77.3374],
      [20.9, 75.6],
      [18.5822, 73.9197],
      [19.0896, 72.8656],
    ],
    path: ['VIDP', 'BHO', 'PNQ', 'VABB'],
    explanation: [
      'A restricted airspace sector makes the direct western corridor unavailable for this demonstration.',
      'The displayed route shifts south-east through the central India corridor and approaches Mumbai via Pune.',
      'The longer path represents a deliberate trade-off: avoid the restricted sector rather than preserve the shortest distance.',
    ],
  },
  {
    id: 'weather',
    name: 'Severe Weather Cell',
    shortName: 'Weather avoidance',
    description: 'A high-severity weather region affects the Gujarat approach corridor.',
    eventLabel: 'Convective weather',
    status: 'WEATHER AVOIDANCE',
    severity: 'HIGH',
    icon: CloudRain,
    distanceKm: 1280,
    etaMin: 117,
    weatherExposureKm: 35,
    congestionExposureKm: 135,
    uncertainty: 0.18,
    score: 1.11,
    hops: 3,
    geometry: [
      [28.5562, 77.1000],
      [26.2, 77.0],
      [22.7218, 75.8011],
      [21.6, 74.3],
      [21.1141, 72.7411],
      [19.0896, 72.8656],
    ],
    path: ['VIDP', 'IDR', 'STV', 'VABB'],
    explanation: [
      'A synthetic high-severity weather cell is placed over the usual western approach corridor.',
      'The route is shifted south through the Indore and Surat area to reduce exposure to the illustrative weather region.',
      'Weather exposure decreases in this scenario, while the additional distance leads to a modest ETA increase. These are demo values, not a live forecast.',
    ],
  },
  {
    id: 'congestion',
    name: 'Traffic Surge',
    shortName: 'Congestion',
    description: 'Elevated traffic cost is around the Jaipur-Ahmedabad corridor.',
    eventLabel: 'Traffic surge',
    status: 'CONGESTION AVOIDANCE',
    severity: 'MODERATE',
    icon: Activity,
    distanceKm: 1260,
    etaMin: 115,
    weatherExposureKm: 95,
    congestionExposureKm: 58,
    uncertainty: 0.15,
    score: 1.07,
    hops: 4,
    geometry: [
      [28.5562, 77.1000],
      [26.8242, 75.8122],
      [24.6177, 73.8961],
      [22.8, 74.8],
      [20.6, 74.1],
      [18.5822, 73.9197],
      [19.0896, 72.8656],
    ],
    path: ['VIDP', 'JAI', 'UDR', 'PNQ', 'VABB'],
    explanation: [
      'A synthetic traffic surge raises the route cost through the Jaipur–Ahmedabad sector.',
      'The alternate route bends through Udaipur and Pune, reducing its illustrative congestion exposure.',
      'The diversion adds distance, but the scenario assumes that the lower traffic penalty offsets part of the extra travel cost.',
    ],
  },
  {
    id: 'surveillance',
    name: 'Surveillance Data Gap',
    shortName: 'Data uncertainty',
    description: 'A temporary surveillance-feed gap increases uncertainty on the reference corridor.',
    eventLabel: 'Feed degradation',
    status: 'UNCERTAINTY-AWARE ROUTING',
    severity: 'MODERATE',
    icon: RadioTower,
    distanceKm: 1270,
    etaMin: 116,
    weatherExposureKm: 100,
    congestionExposureKm: 100,
    uncertainty: 0.31,
    score: 1.10,
    hops: 4,
    geometry: [
      [28.5562, 77.1000],
      [26.7606, 80.8893],
      [24.8, 79.0],
      [23.2875, 77.3374],
      [22.7218, 75.8011],
      [20.8, 74.0],
      [19.0896, 72.8656],
    ],
    path: ['VIDP', 'LKO', 'BHO', 'IDR', 'VABB'],
    explanation: [
      'A surveillance-feed gap reduces confidence in the current state estimate for the reference corridor.',
      'The example planner chooses a more conservative central path instead of relying as heavily on the uncertain sector.',
      'The uncertainty indicator is intentionally illustrative; this static view is not evaluating real sensor availability or flight safety.',
    ],
  },
];

function makeRoute(scenario: DemoScenario): RouteDetail {
  return {
    found: true,
    label: `${scenario.name} · illustrative route`,
    algorithm: 'static-demo',
    path: scenario.path,
    geometry: scenario.geometry,
    totals: {
      distance_km: scenario.distanceKm,
      estimated_time_min: scenario.etaMin,
      weather_exposure_km: scenario.weatherExposureKm,
      congestion_exposure_km: scenario.congestionExposureKm,
      mean_uncertainty: scenario.uncertainty,
      composite_score: scenario.score,
      hops: scenario.hops,
      closed_edges_in_route: 0,
    },
    explanation: scenario.explanation,
  };
}

const formatDelta = (value: number, suffix: string) => `${value > 0 ? '+' : ''}${value}${suffix}`;

export const ScenarioStudioView: React.FC<ScenarioStudioViewProps> = () => {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('normal');

  const selectedScenario = DEMO_SCENARIOS.find((scenario) => scenario.id === selectedScenarioId) ?? DEMO_SCENARIOS[0];
  const selectedRoute = useMemo(() => makeRoute(selectedScenario), [selectedScenario]);
  const isBaseline = selectedScenario.id === 'normal';
  const distanceDelta = selectedScenario.distanceKm - Number(BASELINE_ROUTE.totals?.distance_km ?? 0);
  const timeDelta = selectedScenario.etaMin - Number(BASELINE_ROUTE.totals?.estimated_time_min ?? 0);
  const ScenarioIcon = selectedScenario.icon;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-aerospace-800 bg-aerospace-900 p-5 shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 font-mono text-lg font-bold text-white">
              <Zap className="h-5 w-5 text-amber-400" />
              SCENARIO STUDIO &amp; DYNAMIC REROUTING
            </h2>
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-400">
              Interactive route demonstration. Choose a disruption to switch the displayed route and inspect the reasoning.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setSelectedScenarioId('normal')}
            className="inline-flex items-center gap-2 rounded-lg border border-aerospace-700 bg-aerospace-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-amber-500/60 hover:text-white"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Reset demo
          </button>
        </div>

      
      </section>

      <section>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-cyan-400">SELECT A SCENARIO</p>
            <h3 className="mt-1 text-sm font-semibold text-white">Click a card to change the route</h3>
          </div>
          <span className="text-[11px] text-slate-500">{DEMO_SCENARIOS.length} predefined simulations</span>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {DEMO_SCENARIOS.map((scenario) => {
            const Icon = scenario.icon;
            const active = scenario.id === selectedScenarioId;
            return (
              <button
                type="button"
                key={scenario.id}
                onClick={() => setSelectedScenarioId(scenario.id)}
                aria-pressed={active}
                className={`relative min-h-[142px] rounded-xl border p-4 text-left transition duration-200 ${active ? 'border-cyan-400/80 bg-cyan-950/30 shadow-lg shadow-cyan-950/30 ring-1 ring-cyan-500/20' : 'border-aerospace-800 bg-aerospace-900 hover:border-aerospace-600 hover:bg-aerospace-850'}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <span className={`flex h-9 w-9 items-center justify-center rounded-lg border ${active ? 'border-cyan-500/40 bg-cyan-950 text-cyan-300' : 'border-aerospace-700 bg-aerospace-950 text-slate-300'}`}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className={`rounded px-2 py-1 font-mono text-[9px] font-bold tracking-wide ${scenario.severity === 'HIGH' ? 'border border-red-900 bg-red-950/60 text-red-300' : scenario.severity === 'MODERATE' ? 'border border-amber-900 bg-amber-950/50 text-amber-300' : 'border border-emerald-900 bg-emerald-950/50 text-emerald-300'}`}>
                    {scenario.severity}
                  </span>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <span className="text-sm font-bold text-white">{scenario.name}</span>
                  {active && <CheckCircle2 className="h-4 w-4 shrink-0 text-cyan-300" />}
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">{scenario.description}</p>
              </button>
            );
          })}
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-aerospace-800 bg-aerospace-900 shadow-xl">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-aerospace-800 p-4 sm:p-5">
          <div>
            <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-cyan-400">ACTIVE SIMULATION</p>
            <h3 className="mt-1 flex items-center gap-2 text-base font-bold text-white">
              <ScenarioIcon className="h-5 w-5 text-cyan-300" /> {selectedScenario.name}
            </h3>
            <p className="mt-1 text-xs text-slate-400">Delhi (VIDP) <ArrowRight className="mx-1 inline h-3 w-3" /> Mumbai (VABB)</p>
          </div>
          <span className={`rounded border px-2.5 py-1.5 font-mono text-[10px] font-bold ${isBaseline ? 'border-emerald-800 bg-emerald-950/50 text-emerald-300' : 'border-cyan-800 bg-cyan-950/50 text-cyan-200'}`}>
            {selectedScenario.status}
          </span>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3">
          <div className="p-3 sm:p-4 xl:col-span-2">
            <AirspaceMap
              airports={DEMO_AIRPORTS}
              waypoints={[]}
              edges={[]}
              primaryRoute={selectedRoute}
              secondaryRoute={isBaseline ? null : BASELINE_ROUTE}
              center={[23.5, 77.3]}
              zoom={5}
              height="500px"
            />
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 px-1 text-[11px] text-slate-400">
              <span className="inline-flex items-center gap-2"><i className="h-1 w-6 rounded bg-cyan-400" /> Selected scenario route</span>
              {!isBaseline && <span className="inline-flex items-center gap-2"><i className="h-1 w-6 rounded border-t-2 border-dashed border-amber-400" /> Baseline route</span>}
              <span className="inline-flex items-center gap-2"><i className="h-2.5 w-2.5 rounded-full border border-cyan-300 bg-slate-900" /> Demo airport</span>
            </div>
            <p className="mt-2 text-[10px] leading-relaxed text-slate-500">Map geometry uses fixed example coordinates for a presentation. It is not an operational navigation route.</p>
          </div>

          <aside className="border-t border-aerospace-800 p-4 sm:p-5 xl:border-l xl:border-t-0">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-amber-800/70 bg-amber-950/50 text-amber-300">
                <AlertTriangle className="h-4 w-4" />
              </div>
              <div>
                <p className="font-mono text-[10px] font-bold tracking-wide text-slate-400">EVENT</p>
                <p className="text-sm font-semibold text-white">{selectedScenario.eventLabel}</p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <Metric label="DISTANCE" value={`${selectedScenario.distanceKm.toLocaleString()} km`} delta={isBaseline ? 'REFERENCE' : formatDelta(distanceDelta, ' km')} />
              <Metric label="EST. FLIGHT TIME" value={`${selectedScenario.etaMin} min`} delta={isBaseline ? 'REFERENCE' : formatDelta(timeDelta, ' min')} />
              <Metric label="WEATHER EXPOSURE" value={`${selectedScenario.weatherExposureKm} km`} />
              <Metric label="TRAFFIC EXPOSURE" value={`${selectedScenario.congestionExposureKm} km`} />
            </div>

            <div className="mt-4 rounded-lg border border-aerospace-800 bg-aerospace-950/70 p-3">
              <p className="mb-2 flex items-center gap-2 font-mono text-[10px] font-bold tracking-wide text-slate-300"><Wind className="h-3.5 w-3.5 text-cyan-300" /> ROUTE PROFILE</p>
              <div className="space-y-2 text-xs">
                <ProfileRow label="Average uncertainty" value={`${Math.round(selectedScenario.uncertainty * 100)}%`} />
                <ProfileRow label="Route segments" value={`${selectedScenario.hops}`} />
                <ProfileRow label="Composite cost index" value={selectedScenario.score.toFixed(2)} />
              </div>
            </div>

            <div className="mt-4">
              <p className="mb-2 flex items-center gap-2 font-mono text-[10px] font-bold tracking-wide text-slate-300"><Zap className="h-3.5 w-3.5 text-amber-300" /> EXPLANATION</p>
              <div className="space-y-2">
                {selectedScenario.explanation.map((line, index) => (
                  <div key={`${selectedScenario.id}-${index}`} className="flex gap-2 rounded-lg border border-aerospace-800 bg-aerospace-950/60 p-2.5 text-xs leading-relaxed text-slate-300">
                    <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-aerospace-800 font-mono text-[9px] text-cyan-200">{index + 1}</span>
                    <p>{line}</p>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-aerospace-800 bg-aerospace-950/50 px-4 py-3 text-[10px] text-slate-500 sm:px-5">
          <span className="inline-flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" /> Illustrative metrics · not live inference</span>
          <span className="font-mono">SCENARIO ID: {selectedScenario.id.toUpperCase()}</span>
        </div>
      </section>
    </div>
  );
};

function Metric({ label, value, delta }: { label: string; value: string; delta?: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-aerospace-800 bg-aerospace-950 p-3">
      <p className="truncate font-mono text-[9px] font-semibold tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-base font-bold tabular-nums text-white">{value}</p>
      {delta && <p className={`mt-1 text-[10px] font-mono ${delta.startsWith('+') ? 'text-amber-300' : 'text-emerald-300'}`}>{delta}</p>}
    </div>
  );
}

function ProfileRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono font-semibold tabular-nums text-slate-200">{value}</span>
    </div>
  );
}
