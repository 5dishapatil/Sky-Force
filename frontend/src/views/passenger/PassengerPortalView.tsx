import React, { useState, useEffect } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bell,
  Calendar,
  CheckCircle2,
  Clock,
  Compass,
  FileQuestion,
  HelpCircle,
  Info,
  Layers,
  MapPin,
  Plane,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
  User,
  Wind,
} from 'lucide-react';
import type { FlightSummary, FlightDetail, OperationalStage } from '../../types';
import { api } from '../../services/api';

interface PassengerPortalViewProps {
  onSwitchToOperations: () => void;
  onInspectRouteInOperations?: (origin: string, destination: string) => void;
}

export const PassengerPortalView: React.FC<PassengerPortalViewProps> = ({
  onSwitchToOperations,
  onInspectRouteInOperations,
}) => {
  const [activePassengerTab, setActivePassengerTab] = useState<'my-flight' | 'timeline' | 'alternatives' | 'notifications' | 'about'>('my-flight');

  // Search States
  const [searchQuery, setSearchQuery] = useState('304');
  const [selectedDate, setSelectedDate] = useState('2026-01-15');
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Flight Data
  const [selectedFlight, setSelectedFlight] = useState<FlightDetail | null>(null);
  const [recentFlights, setRecentFlights] = useState<FlightSummary[]>([]);

  // Demo Notification Simulation
  const [notifications, setNotifications] = useState<
    { id: string; time: string; title: string; body: string; type: 'info' | 'warning' | 'good' }[]
  >([
    {
      id: '1',
      time: '10 mins ago',
      title: 'Gate Information Updated',
      body: 'Flight assigned to Terminal 3, Gate 42B. Security checkpoints operating normally.',
      type: 'info',
    },
    {
      id: '2',
      time: '25 mins ago',
      title: 'Inbound Aircraft En-Route',
      body: 'Assigned airframe SF0001 is on descent. Ground turnaround crew alerted.',
      type: 'good',
    },
    {
      id: '3',
      time: '45 mins ago',
      title: 'Departure Window Advisory',
      body: 'Weather conditions at departure airport are VFR clear. Airway traffic flow is nominal.',
      type: 'info',
    },
  ]);

  // Initial Load: Find default flight
  useEffect(() => {
    let cancelled = false;
    const fetchInitial = async () => {
      setLoading(true);
      try {
        const res = await api.getDelayFlights({ query: '304', limit: 5 });
        if (cancelled) return;
        if (res.flights && res.flights.length > 0) {
          setRecentFlights(res.flights);
          const detail = await api.getDelayFlightDetail(res.flights[0].flight_id);
          if (cancelled) return;
          setSelectedFlight(detail);
        }
      } catch (err) {
        if (!cancelled) {
          setSearchError(err instanceof Error ? err.message : 'Could not load flights');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchInitial();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSearch = async (queryText: string) => {
    setLoading(true);
    setSearchError(null);
    try {
      const res = await api.getDelayFlights({ query: queryText, limit: 10 });
      if (!res.flights || res.flights.length === 0) {
        setSearchError(`No flights found matching "${queryText}". Try quick demo chips below.`);
        setLoading(false);
        return;
      }
      setRecentFlights(res.flights);
      const detail = await api.getDelayFlightDetail(res.flights[0].flight_id);
      setSelectedFlight(detail);
      setActivePassengerTab('my-flight');
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Search failed. Check API status.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectFlight = async (flightId: string) => {
    setLoading(true);
    setSearchError(null);
    try {
      const detail = await api.getDelayFlightDetail(flightId);
      setSelectedFlight(detail);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Could not fetch flight details.');
    } finally {
      setLoading(false);
    }
  };

  // Helper for status badge styling
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ON_SCHEDULE':
        return {
          label: 'On Schedule',
          color: 'bg-emerald-950/80 text-emerald-300 border-emerald-600/70',
          dot: 'bg-emerald-400',
        };
      case 'DELAY_LIKELY':
        return {
          label: 'Delay Likely',
          color: 'bg-amber-950/80 text-amber-300 border-amber-600/70',
          dot: 'bg-amber-400',
        };
      case 'SIGNIFICANT_DELAY_LIKELY':
        return {
          label: 'Significant Delay',
          color: 'bg-rose-950/80 text-rose-300 border-rose-600/70',
          dot: 'bg-rose-400',
        };
      default:
        return {
          label: 'Estimate Uncertain',
          color: 'bg-slate-800 text-slate-300 border-slate-600',
          dot: 'bg-slate-400',
        };
    }
  };

  const statusBadge = selectedFlight ? getStatusBadge(selectedFlight.status) : null;

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Top Banner: Passenger Role & Quick Role Switcher */}
      <div className="bg-gradient-to-r from-cyan-950/80 via-aerospace-900 to-blue-950/80 border border-cyan-800/60 rounded-xl p-4 shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-sm">
            <User size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold tracking-wider text-cyan-400 uppercase">PASSENGER PORTAL</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-900/60 text-cyan-300 border border-cyan-700/60 font-semibold">
                DEMONSTRATION ESTIMATE
              </span>
            </div>
            <h2 className="text-base font-bold text-white">Flight Departure Status & Delay Assistant</h2>
          </div>
        </div>

        <button
          type="button"
          onClick={onSwitchToOperations}
          className="self-start sm:self-auto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-aerospace-950/90 border border-cyan-700/60 text-cyan-300 hover:text-white hover:bg-cyan-900/40 transition-all text-xs font-semibold cursor-pointer shadow-sm"
        >
          <Compass size={13} />
          <span>Switch to Operations Console</span>
          <ArrowRight size={13} />
        </button>
      </div>

      {/* Passenger Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-aerospace-800 pb-2">
        <button
          type="button"
          onClick={() => setActivePassengerTab('my-flight')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activePassengerTab === 'my-flight'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-sm font-bold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-aerospace-900'
          }`}
        >
          <Plane size={14} />
          <span>My Flight</span>
        </button>

        <button
          type="button"
          onClick={() => setActivePassengerTab('timeline')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activePassengerTab === 'timeline'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-sm font-bold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-aerospace-900'
          }`}
        >
          <Clock size={14} />
          <span>Departure Progress (8 Stages)</span>
        </button>

        <button
          type="button"
          onClick={() => setActivePassengerTab('alternatives')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activePassengerTab === 'alternatives'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-sm font-bold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-aerospace-900'
          }`}
        >
          <Layers size={14} />
          <span>Alternative Flights</span>
        </button>

        <button
          type="button"
          onClick={() => setActivePassengerTab('notifications')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activePassengerTab === 'notifications'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-sm font-bold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-aerospace-900'
          }`}
        >
          <Bell size={14} />
          <span>Live Updates</span>
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
        </button>

        <button
          type="button"
          onClick={() => setActivePassengerTab('about')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ml-auto ${
            activePassengerTab === 'about'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-sm font-bold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-aerospace-900'
          }`}
        >
          <Info size={14} />
          <span>About This Forecast</span>
        </button>
      </div>

      {/* Flight Search Bar & Quick Demo Chips */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-4 shadow-lg space-y-3">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch(searchQuery)}
              placeholder="Enter flight number (e.g. 304, SF 304, SFD113) or airport code (DEL, BOM)..."
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-aerospace-950 border border-aerospace-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>

          <button
            type="button"
            onClick={() => handleSearch(searchQuery)}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            <span>Track Flight</span>
          </button>
        </div>

        {/* Quick Demo Flights Chips */}
        <div className="flex flex-wrap items-center gap-2 text-xs pt-1">
          <span className="text-slate-400 text-[11px] font-mono">Demo Flights:</span>
          {[
            { label: 'SF 304 (DEL -> BLR)', query: '304', note: 'Nominal' },
            { label: 'SF 100 (PNQ -> BOM)', query: '100', note: 'On-Time' },
            { label: 'SF 113 (HYD -> CCU)', query: '113', note: 'Weather Delay' },
            { label: 'SF 412 (HYD -> BOM)', query: '412', note: 'Inbound Leg' },
          ].map((chip) => (
            <button
              key={chip.query}
              type="button"
              onClick={() => {
                setSearchQuery(chip.query);
                handleSearch(chip.query);
              }}
              className="px-2.5 py-1 rounded bg-aerospace-950 border border-aerospace-800 hover:border-cyan-500/60 text-slate-300 hover:text-white text-[11px] font-mono transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <span>{chip.label}</span>
              <span className="text-[9px] text-cyan-400 font-sans">({chip.note})</span>
            </button>
          ))}
        </div>

        {searchError && (
          <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle size={15} />
            <span>{searchError}</span>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: MY FLIGHT STATUS CARD & EXPLANATION                                */}
      {/* ========================================================================= */}
      {activePassengerTab === 'my-flight' && selectedFlight && (
        <div className="space-y-6">
          {/* Main Flight Status Card */}
          <div className="bg-aerospace-900 border border-aerospace-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

            {/* Flight Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-aerospace-800">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg font-bold font-mono text-white">{selectedFlight.flight_number}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-aerospace-950 text-slate-400 border border-aerospace-800 font-mono">
                    Callsign: {selectedFlight.callsign}
                  </span>
                  <span className="text-xs text-slate-400">· {selectedFlight.airline}</span>
                </div>
                <div className="text-xs text-slate-400 font-mono">
                  Assigned Aircraft: <span className="text-cyan-400 font-bold">{selectedFlight.aircraft_tail}</span>
                </div>
              </div>

              {/* Status Pill */}
              {statusBadge && (
                <div className={`px-3 py-1.5 rounded-full border flex items-center gap-2 text-xs font-bold ${statusBadge.color}`}>
                  <span className={`w-2 h-2 rounded-full ${statusBadge.dot} animate-pulse`} />
                  <span>{statusBadge.label}</span>
                  {selectedFlight.predicted_delay_minutes > 0 && (
                    <span className="text-xs opacity-90 font-mono">
                      (+{Math.round(selectedFlight.predicted_delay_minutes)} min)
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Origin & Destination Display */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 my-6 items-center">
              {/* Origin */}
              <div className="space-y-1">
                <span className="text-[11px] font-mono text-slate-400 uppercase">DEPARTURE AIRPORT</span>
                <div className="text-3xl font-black font-mono text-cyan-400">{selectedFlight.origin_iata}</div>
                <div className="text-xs font-semibold text-slate-200">{selectedFlight.origin_name}</div>
                <div className="text-[11px] text-slate-400 flex items-center gap-1">
                  <Wind size={12} className="text-cyan-400" />
                  <span>{selectedFlight.departure_weather_summary.condition || 'Fair / VFR'}</span>
                </div>
              </div>

              {/* Mid Flight Path & Distance */}
              <div className="flex flex-col items-center justify-center text-center space-y-2 py-2">
                <div className="w-full flex items-center gap-2 text-slate-600">
                  <div className="flex-1 border-t border-dashed border-slate-700" />
                  <Plane className="w-5 h-5 text-cyan-400 rotate-90" />
                  <div className="flex-1 border-t border-dashed border-slate-700" />
                </div>
                <div className="text-[11px] font-mono text-slate-400">
                  {selectedFlight.enroute_distance_km} km · Est. flight duration: ~{Math.round(selectedFlight.enroute_time_minutes)} min
                </div>
                {onInspectRouteInOperations && (
                  <button
                    type="button"
                    onClick={() => onInspectRouteInOperations(selectedFlight.origin_id, selectedFlight.destination_id)}
                    className="text-[11px] text-cyan-400 hover:text-cyan-300 hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    <span>Inspect airway route in Route Lab</span>
                    <ArrowRight size={11} />
                  </button>
                )}
              </div>

              {/* Destination */}
              <div className="space-y-1 md:text-right">
                <span className="text-[11px] font-mono text-slate-400 uppercase">ARRIVAL AIRPORT</span>
                <div className="text-3xl font-black font-mono text-blue-400">{selectedFlight.destination_iata}</div>
                <div className="text-xs font-semibold text-slate-200">{selectedFlight.destination_name}</div>
                <div className="text-[11px] text-slate-400 md:justify-end flex items-center gap-1">
                  <MapPin size={12} className="text-blue-400" />
                  <span>Scheduled Arrival: {new Date(selectedFlight.scheduled_arrival_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </div>
            </div>

            {/* Time Comparison & Gate vs Takeoff Breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 p-4 rounded-xl bg-aerospace-950 border border-aerospace-800 text-xs">
              <div className="space-y-1">
                <span className="text-slate-400 text-[11px]">Scheduled Departure (STD):</span>
                <div className="text-sm font-bold font-mono text-white">
                  {new Date(selectedFlight.scheduled_departure_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
                <div className="text-[10px] text-slate-500">Timetable scheduled gate off-block</div>
              </div>

              <div className="space-y-1 border-l sm:border-l-0 lg:border-l border-aerospace-800 sm:pl-0 lg:pl-3">
                <span className="text-cyan-400 text-[11px] font-semibold">Estimated Gate Pushback:</span>
                <div className="text-sm font-bold font-mono text-cyan-300">
                  {new Date(selectedFlight.estimated_gate_departure_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
                <div className="text-[10px] text-slate-500">Predicted off-block time</div>
              </div>

              <div className="space-y-1 border-l border-aerospace-800 pl-3">
                <span className="text-blue-400 text-[11px] font-semibold">Estimated Runway Take-Off:</span>
                <div className="text-sm font-bold font-mono text-blue-300">
                  {new Date(selectedFlight.estimated_takeoff_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
                <div className="text-[10px] text-slate-500">Includes ~{Math.round(selectedFlight.taxi_time_minutes)} min taxi-out</div>
              </div>

              <div className="space-y-1 border-l border-aerospace-800 pl-3">
                <span className="text-amber-400 text-[11px] font-semibold">Delay Interval Estimate:</span>
                <div className="text-sm font-bold font-mono text-amber-300">
                  {selectedFlight.predicted_delay_minutes === 0 ? '0 min' : `${selectedFlight.delay_interval_min} – ${selectedFlight.delay_interval_max} min`}
                </div>
                <div className="text-[10px] text-slate-500">Confidence: {selectedFlight.confidence_label} ({Math.round(selectedFlight.confidence_score * 100)}%)</div>
              </div>
            </div>

            {/* Plain English Prediction Card */}
            <div className="mt-4 p-4 rounded-xl bg-cyan-950/30 border border-cyan-800/40 text-xs space-y-1">
              <div className="flex items-center gap-1.5 text-cyan-400 font-bold">
                <Sparkles size={14} />
                <span>Plain-English Delay Assessment</span>
              </div>
              <p className="text-slate-200 leading-relaxed font-sans">
                {selectedFlight.explanation_plain_english}
              </p>
              <div className="text-[10px] text-slate-400 pt-1 flex items-center justify-between">
                <span>Data Freshness: Updated based on latest surveillance pass · Synthetic demonstration corpus</span>
                <span className="font-mono text-slate-500">Source: {selectedFlight.data_source}</span>
              </div>
            </div>
          </div>

          {/* Contributing Factors Section with Strict Evidence Attributions */}
          <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-cyan-400" />
                  WHY MIGHT THIS FLIGHT BE DELAYED? (FACTOR ATTRIBUTIONS)
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Every factor is explicitly tagged as Confirmed, Model-Inferred, or Unavailable.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {selectedFlight.factors.map((factor, idx) => {
                const isConfirmed = factor.evidence_status === 'CONFIRMED';
                const isInferred = factor.evidence_status === 'MODEL_INFERRED';
                const isUnavailable = factor.evidence_status === 'UNAVAILABLE';

                return (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1.5 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-bold text-slate-200">{factor.name}</span>
                        <span
                          className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                            isConfirmed
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : isInferred
                              ? 'bg-blue-950 text-blue-300 border border-blue-800'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {factor.evidence_status.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-slate-300 leading-relaxed text-[11px] font-sans">
                        {factor.description}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-aerospace-800/80 flex items-center justify-between text-[10px] text-slate-400">
                      <span>Source: {factor.source}</span>
                      {factor.impact_minutes > 0 ? (
                        <span className="text-amber-400 font-mono font-bold">+{factor.impact_minutes} min impact</span>
                      ) : (
                        <span className="text-slate-500 font-mono">0 min</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: DEPARTURE PROGRESS TIMELINE (8 OPERATIONAL STAGES)                 */}
      {/* ========================================================================= */}
      {activePassengerTab === 'timeline' && selectedFlight && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              OPERATIONAL FLIGHT PROGRESS TIMELINE (8 CHRONOLOGICAL STAGES)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Tracking flight from schedule release through airframe rotation, weather, and takeoff.
            </p>
          </div>

          <div className="relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-aerospace-800">
            {selectedFlight.timeline.map((stage) => {
              const isDone = stage.status === 'COMPLETED';
              const isDelayed = stage.status === 'DELAYED';
              const isActive = stage.status === 'ACTIVE';

              return (
                <div key={stage.stage_id} className="relative group">
                  {/* Dot */}
                  <span
                    className={`absolute -left-6 top-1.5 w-3 h-3 rounded-full border-2 transition-all ${
                      isDone
                        ? 'bg-emerald-500 border-emerald-300'
                        : isDelayed
                        ? 'bg-rose-500 border-rose-300 animate-pulse'
                        : isActive
                        ? 'bg-cyan-500 border-cyan-300 animate-pulse'
                        : 'bg-aerospace-950 border-slate-600'
                    }`}
                  />

                  <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-cyan-400">Stage {stage.stage_number}:</span>
                        <span className="text-xs font-bold text-white">{stage.stage_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] text-slate-300 font-semibold">{stage.time_display}</span>
                        <span
                          className={`text-[9px] font-mono px-2 py-0.5 rounded uppercase font-semibold ${
                            stage.evidence_status === 'CONFIRMED'
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : 'bg-blue-950 text-blue-300 border border-blue-800'
                          }`}
                        >
                          {stage.evidence_status}
                        </span>
                      </div>
                    </div>
                    <p className="text-slate-300 text-xs leading-relaxed font-sans">{stage.explanation}</p>
                    <div className="text-[10px] text-slate-500 pt-1">Data Source: {stage.source}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: ALTERNATIVE FLIGHTS                                                */}
      {/* ========================================================================= */}
      {activePassengerTab === 'alternatives' && selectedFlight && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              ALTERNATIVE FLIGHTS ({selectedFlight.origin_iata} ➔ {selectedFlight.destination_iata})
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Available flights operating on the same city pair within the scheduled window.
            </p>
          </div>

          {selectedFlight.alternative_flights.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-aerospace-950 text-slate-400 font-mono uppercase text-[10px] border-b border-aerospace-800">
                  <tr>
                    <th className="p-3">Flight</th>
                    <th className="p-3">Aircraft</th>
                    <th className="p-3">Scheduled Dep</th>
                    <th className="p-3">Estimated Dep</th>
                    <th className="p-3">Delay Risk</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-aerospace-800/60 font-sans">
                  {selectedFlight.alternative_flights.map((alt) => {
                    const badge = getStatusBadge(alt.status);
                    return (
                      <tr key={alt.flight_id} className="hover:bg-aerospace-950/60 transition-colors">
                        <td className="p-3 font-mono font-bold text-cyan-300">{alt.flight_number}</td>
                        <td className="p-3 font-mono text-slate-400">{alt.aircraft_tail}</td>
                        <td className="p-3">{new Date(alt.scheduled_departure_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                        <td className="p-3 font-semibold text-white">{new Date(alt.estimated_departure_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${badge.color}`}>
                            {badge.label} (+{Math.round(alt.predicted_delay_minutes)}m)
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          <button
                            type="button"
                            onClick={() => handleSelectFlight(alt.flight_id)}
                            className="px-2.5 py-1 rounded bg-aerospace-800 hover:bg-cyan-600 text-white text-[11px] font-semibold transition-all cursor-pointer"
                          >
                            Inspect Flight
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-6 text-center text-slate-400 text-xs">
              No alternative flights scheduled on this city pair within the current time window.
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: LIVE UPDATES / NOTIFICATIONS                                       */}
      {/* ========================================================================= */}
      {activePassengerTab === 'notifications' && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
              <Bell className="w-4 h-4 text-cyan-400" />
              FLIGHT EVENT NOTIFICATIONS & ADVISORIES
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Simulated passenger advisories from gate, air traffic sequencing, and airframe monitoring.
            </p>
          </div>

          <div className="space-y-3">
            {notifications.map((item) => (
              <div
                key={item.id}
                className="p-4 rounded-lg bg-aerospace-950 border border-aerospace-800 flex items-start gap-3"
              >
                <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/40 text-cyan-400 mt-0.5">
                  <Bell size={14} />
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">{item.title}</span>
                    <span className="text-[10px] font-mono text-slate-500">{item.time}</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">{item.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: ABOUT THIS FORECAST & TRANSPARENCY                                  */}
      {/* ========================================================================= */}
      {activePassengerTab === 'about' && (
        <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-6 shadow-lg space-y-4 text-xs">
          <div className="flex items-center gap-2 text-white font-mono font-bold text-sm">
            <Info className="w-4 h-4 text-cyan-400" />
            <span>ABOUT SKY FORCE FLIGHT DELAY ESTIMATES</span>
          </div>

          <div className="space-y-3 text-slate-300 leading-relaxed font-sans">
            <p>
              <strong>Academic & Research Disclaimer:</strong> Sky Force is an academic aviation intelligence simulation
              prototype. The departure delay estimates shown here are produced by an explainable scenario estimator
              combining aircraft rotation tracking, airport departure bank sizing, and atmospheric grid weather data.
            </p>
            <p>
              <strong>Distinction of Events:</strong>
              <ul className="list-disc list-inside mt-1 space-y-1 text-slate-400 font-mono text-[11px]">
                <li><strong>Scheduled Departure Time (STD):</strong> Timetable gate departure time.</li>
                <li><strong>Estimated Gate Departure:</strong> Estimated off-block pushback time based on rotation and servicing.</li>
                <li><strong>Estimated Runway Take-Off:</strong> Includes taxi-out sequencing across airport aprons and queues.</li>
              </ul>
            </p>
            <p>
              <strong>Honesty About Missing Data:</strong> Flight delays can stem from cabin crew shortages, mechanical defects,
              baggage loading holds, or air traffic flow management slot revisions. When these factors cannot be confirmed
              from available surveillance telemetry, they are explicitly labelled as <code>UNAVAILABLE</code> rather than
              invented.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
