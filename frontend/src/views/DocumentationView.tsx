import React from 'react';
import { 
  BookOpen, 
  HelpCircle, 
  CheckCircle2, 
  Code, 
  FileText, 
  AlertTriangle,
  Lightbulb,
  ShieldCheck
} from 'lucide-react';

export const DocumentationView: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg">
        <h2 className="text-lg font-bold text-white flex items-center gap-2 font-mono">
          <BookOpen className="w-5 h-5 text-cyan-400" />
          RESEARCH QUESTIONS & ACADEMIC VIVA GUIDE
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Comprehensive project defense documentation, theoretical guarantees, and examiner FAQ
        </p>
      </div>

      {/* 6 Research Hypotheses */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
        <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-400" />
          RESEARCH QUESTIONS & EXPERIMENTAL FINDINGS
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1.5">
            <div className="text-cyan-400 font-mono font-bold">RQ1: Spatial Traffic Indicators</div>
            <p className="text-slate-300 leading-relaxed font-sans">
              <strong>Finding:</strong> Converting 90s surveillance telemetry into half-open 2.0° grid cells with causal 
              lagged counts produces highly informative indicators of density, capturing corridor choke points cleanly.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1.5">
            <div className="text-cyan-400 font-mono font-bold">RQ2: Leakage-Free ML Forecasting</div>
            <p className="text-slate-300 leading-relaxed font-sans">
              <strong>Finding:</strong> The Random Forest classifier achieves 84.7% test accuracy (Macro-F1 0.636) 
              for the next 15-minute window, significantly outperforming Zero-R baseline (0.312) under chronological partitioning.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1.5">
            <div className="text-cyan-400 font-mono font-bold">RQ3: Multi-Objective Routing vs Distance</div>
            <p className="text-cyan-300 leading-relaxed font-sans">
              <strong>Finding:</strong> Under weather storm zones or corridor closures, composite multi-factor routing 
              successfully routes aircraft around hazards with minor distance increases (+3.8% to +7.2% length penalty).
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1.5">
            <div className="text-cyan-400 font-mono font-bold">RQ4: Natural Language Explainability</div>
            <p className="text-slate-300 leading-relaxed font-sans">
              <strong>Finding:</strong> Decomposing route cost into dimensionless factors allows instant transparent 
              explanations of trade-offs (e.g. "Selected route trades +45 km distance to avoid 180 km of severe weather").
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1.5">
            <div className="text-cyan-400 font-mono font-bold">RQ5: Dynamic Rerouting Resiliency</div>
            <p className="text-slate-300 leading-relaxed font-sans">
              <strong>Finding:</strong> When hard segment closures occur after departure, the dynamic planner 
              identifies the nearest viable diverging waypoint and calculates compliant alternatives in &lt;15 ms.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1.5">
            <div className="text-cyan-400 font-mono font-bold">RQ6: Baseline Comparison Integrity</div>
            <p className="text-slate-300 leading-relaxed font-sans">
              <strong>Finding:</strong> Comparing against classical baselines (Zero-R, Ridge, Dijkstra shortest distance) 
              prevents overstating ML claims while proving clear statistical and operational utility.
            </p>
          </div>
        </div>
      </div>

      {/* Viva / Project Defense Questions */}
      <div className="bg-aerospace-900 border border-aerospace-800 rounded-xl p-5 shadow-lg space-y-4">
        <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-cyan-400" />
          EXAMINER VIVA DEFENSE GUIDE (Q&A)
        </h3>

        <div className="space-y-3 text-xs font-sans">
          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1">
            <div className="text-white font-bold font-mono">
              Q1: Why did you use graph search (Dijkstra / A*) instead of pure deep reinforcement learning for routing?
            </div>
            <p className="text-slate-300 leading-relaxed">
              <strong>Answer:</strong> Graph search on candidate airway networks provides mathematical optimality, deterministic 
              execution, and strict compliance with hard airspace closures. Deep RL can hallucinate infeasible waypoints and cannot 
              guarantee safety constraints or triangle-inequality bounds.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1">
            <div className="text-white font-bold font-mono">
              Q2: How do you prove your A* heuristic is admissible?
            </div>
            <p className="text-slate-300 leading-relaxed">
              <strong>Answer:</strong> The great-circle Haversine formula strictly satisfies the spherical triangle inequality. 
              The heuristic coefficient scales distance and time terms using the maximum network speed <code>v_max</code>:
              <code>h(n) = [(w_d + ε)/ref_km + w_t/(v_max * ref_min)] * d_gc(n, goal)</code>. Because weather and congestion penalties 
              are non-negative, <code>h(n) ≤ c*(n)</code> is guaranteed, ensuring A* never overestimates true cost.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1">
            <div className="text-white font-bold font-mono">
              Q3: How do you prevent data leakage in your machine learning models?
            </div>
            <p className="text-slate-300 leading-relaxed">
              <strong>Answer:</strong> We enforce strict chronological train/val/test splits (Days 1–4 train, 5–6 val, 7–8 test). 
              Rolling statistics strictly use windows ending before or at the prediction timestamp. Targets are derived strictly 
              from subsequent windows and purged across partition boundaries.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-aerospace-950 border border-aerospace-800 space-y-1">
            <div className="text-white font-bold font-mono">
              Q4: How does Sky Force handle segment closures?
            </div>
            <p className="text-slate-300 leading-relaxed">
              <strong>Answer:</strong> Closures are treated as hard graph constraints (edges are removed or excluded during cost evaluation), 
              never as soft penalties. This ensures no generated route will ever traverse a closed or restricted corridor.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
