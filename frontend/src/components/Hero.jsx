import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  Cpu,
  FileText,
  GitBranch,
  Network,
  Radio,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

const agents = [
  { id: "performance", name: "Performance", responsibility: "Latency · loss · throughput", icon: Activity, position: "top" },
  { id: "infrastructure", name: "Infrastructure", responsibility: "Device health · errors", icon: Cpu, position: "right-top" },
  { id: "connectivity", name: "Connectivity", responsibility: "Links · reachability", icon: Network, position: "right-bottom" },
  { id: "correlation", name: "Fault correlation", responsibility: "Evidence · hypotheses", icon: GitBranch, position: "left-bottom" },
  { id: "reporting", name: "Recommendations", responsibility: "Report · next checks", icon: FileText, position: "left-top" },
];

function AgentNetwork() {
  return (
    <div className="agent-orbit-shell" aria-label="Five connected NetCoop AI analysis stages" role="img">
      <div className="agent-orbit-glow" />
      <div className="agent-orbit-ring agent-orbit-ring--outer" />
      <div className="agent-orbit-ring agent-orbit-ring--inner" />
      <svg className="agent-orbit-links" viewBox="0 0 100 100" aria-hidden="true">
        <defs>
          <linearGradient id="agent-flow" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0" stopColor="#818cf8" stopOpacity=".22" />
            <stop offset="1" stopColor="#c4b5fd" stopOpacity=".92" />
          </linearGradient>
          <marker id="agent-arrow" markerWidth="5.5" markerHeight="5.5" refX="4.5" refY="2.75" orient="auto">
            <path d="M0,0 L5.5,2.75 L0,5.5 z" fill="#c4b5fd" />
          </marker>
        </defs>
        <path className="agent-flow-line" d="M50 11 C50 20 50 29 50 36" markerEnd="url(#agent-arrow)" />
        <path className="agent-flow-line" d="M75 29 C71 34 67 40 63 46" markerEnd="url(#agent-arrow)" />
        <path className="agent-flow-line" d="M68 84 C66 75 64 66 63 57" markerEnd="url(#agent-arrow)" />
        <path className="agent-flow-line agent-flow-line--synthesis" d="M38 56 C35 63 33 69 33 76" markerEnd="url(#agent-arrow)" />
        <path className="agent-flow-line agent-flow-line--synthesis" d="M26 72 C20 61 17 48 18 34" markerEnd="url(#agent-arrow)" />
      </svg>

      <div className="agent-orbit-core">
        <span className="agent-orbit-core__icon"><Sparkles size={21} /></span>
        <small>NETCOOP ORCHESTRATOR</small>
        <strong>One shared<br />diagnosis</strong>
        <span className="agent-orbit-core__caption"><i /> Evidence linked</span>
      </div>

      {agents.map(({ id, name, responsibility, icon: Icon, position }, index) => (
        <article
          className={`agent-orbit-node agent-orbit-node--${position}`}
          key={id}
          style={{ "--agent-delay": `${index * 120}ms` }}
        >
          <span className="agent-orbit-node__icon"><Icon size={16} /></span>
          <span className="agent-orbit-node__copy"><strong>{name}</strong><small>{responsibility}</small></span>
          <span className="agent-orbit-node__number">0{index + 1}</span>
        </article>
      ))}

      <div className="agent-orbit-label agent-orbit-label--inputs">01–03 · DOMAIN ANALYSIS</div>
      <div className="agent-orbit-label agent-orbit-label--outputs">04–05 · CORRELATE & REPORT</div>
    </div>
  );
}

export default function Hero() {
  return (
    <section className="relative overflow-hidden pt-28 pb-14 md:pt-32 md:pb-16 lg:pt-36 lg:pb-20">
      <div className="absolute inset-0 pointer-events-none" style={{ background: "radial-gradient(ellipse 85% 70% at 70% 42%, rgba(99,102,241,.11), transparent 62%), linear-gradient(180deg, rgba(3,3,5,.34), #030305 98%)" }} aria-hidden="true" />

      <div className="container relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-[0.82fr_1.18fr] gap-8 lg:gap-2 items-center">
          <div className="relative z-10 flex flex-col items-center text-center lg:items-start lg:text-left">
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }} className="badge-pill mb-6">
              <Radio className="w-3 h-3 text-indigo-300" />
              MULTI-AGENT NETWORK DIAGNOSTICS
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.08 }}
              className="max-w-3xl text-5xl md:text-6xl xl:text-[4.7rem] font-bold text-white leading-[1.02] tracking-tight"
              style={{ fontFamily: "'Outfit', sans-serif" }}
            >
              Network faults,<br />
              <span className="gradient-text">made understandable.</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.2 }}
              className="text-base md:text-lg text-white/70 max-w-xl mt-6 mb-6 leading-relaxed"
            >
              Five focused agents inspect the telemetry you provide, connect the evidence, and turn a complex network incident into a diagnosis your team can investigate.
            </motion.p>

            <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
              <a href="/dashboard/diagnose" className="btn-primary inline-flex items-center justify-center gap-2 text-white font-semibold px-7 py-3.5 rounded-xl text-sm w-full sm:w-auto">
                Run a diagnosis <ArrowRight className="w-4 h-4" />
              </a>
              <a href="#evidence" className="btn-ghost inline-flex items-center justify-center gap-2 text-white/75 hover:text-white font-medium px-7 py-3.5 rounded-xl text-sm w-full sm:w-auto">
                View sample report <ShieldCheck className="w-4 h-4 text-indigo-300" />
              </a>
            </div>

            <div className="mt-7 flex flex-wrap items-center justify-center lg:justify-start gap-x-5 gap-y-2 text-xs text-white/45">
              <span className="inline-flex items-center gap-2"><i className="agent-status-dot" /> Uses submitted telemetry</span>
              <span className="hidden sm:inline text-white/15">/</span>
              <span>No background polling or fabricated live readings</span>
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.94, x: 18 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.18 }}
            className="relative flex justify-center lg:justify-end"
          >
            <AgentNetwork />
          </motion.div>
        </div>

        <div className="hero-proof-strip mt-4 lg:mt-1">
          <div><strong>05</strong><span>connected stages</span></div>
          <i />
          <div><strong>03</strong><span>independent domain analyses</span></div>
          <i />
          <div><strong><Activity size={17} /></strong><span>evidence-linked output</span></div>
        </div>
      </div>
    </section>
  );
}
