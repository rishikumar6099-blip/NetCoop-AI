import { motion } from "framer-motion";
import { Activity, Cpu, FileText, GitBranch, Network } from "lucide-react";
import { useScrollReveal, staggerContainer, staggerItem } from "@/hooks/useScrollReveal";

const supportingAgents = [
  {
    icon: <Network className="w-5 h-5 text-violet-400" />,
    iconBg: "bg-violet-500/10 border-violet-500/20",
    title: "Connectivity Analysis",
    desc: "Examines supplied devices, links, reachability, network segments and incident scope.",
    visual: (
      <div className="agent-feature-visual">
        <div className="agent-feature-visual__label">Topology map · illustrative</div>
        <svg viewBox="0 0 250 52" className="w-full h-14" aria-hidden="true">
          <path d="M28 27 H82 M82 27 L130 12 M82 27 L130 42 M130 12 H218 M130 42 H218" fill="none" stroke="rgba(129,140,248,.45)" strokeWidth="1.5" />
          {[ [28,27], [82,27], [130,12], [130,42], [218,12], [218,42] ].map(([cx, cy], index) => <g key={`${cx}-${cy}`}><circle cx={cx} cy={cy} r="7" fill="#111225" stroke={index === 1 ? "#a78bfa" : "#6366f1"} strokeWidth="1.5" /><circle cx={cx} cy={cy} r="2" fill={index === 1 ? "#c4b5fd" : "#818cf8"} /></g>)}
        </svg>
        <div className="flex justify-between text-[10px] text-white/50"><span>Devices</span><span>Links</span><span>Reachability</span></div>
      </div>
    ),
  },
  {
    icon: <GitBranch className="w-5 h-5 text-indigo-400" />,
    iconBg: "bg-indigo-500/10 border-indigo-500/20",
    title: "Fault Correlation",
    desc: "Compares specialist findings, ranks supported causes and keeps conflicting evidence visible.",
    visual: (
      <div className="agent-feature-visual">
        <div className="agent-feature-visual__label">Evidence handoff</div>
        <div className="flex items-center gap-1.5 text-[10px]">
          <span className="rounded-md border border-indigo-400/15 bg-indigo-500/[0.08] px-2 py-1.5 text-indigo-200/80">Performance</span>
          <span className="text-violet-300">+</span>
          <span className="rounded-md border border-violet-400/15 bg-violet-500/[0.08] px-2 py-1.5 text-violet-200/80">Infrastructure</span>
          <span className="ml-auto text-indigo-300">→</span>
        </div>
        <div className="mt-2 rounded-md border border-white/[0.06] bg-white/[0.025] px-2.5 py-2 text-[10px] text-white/60">Ranked hypothesis · source references retained</div>
      </div>
    ),
  },
  {
    icon: <FileText className="w-5 h-5 text-violet-400" />,
    iconBg: "bg-violet-500/10 border-violet-500/20",
    title: "Recommendation & Reporting",
    desc: "Produces a traceable diagnosis with limitations, evidence references and practical next checks.",
    visual: (
      <div className="agent-feature-visual">
        <div className="agent-feature-visual__label">Report sections</div>
        <div className="flex flex-wrap gap-1.5">
          {["Probable cause", "Confidence", "Evidence", "Actions"].map((item) => <span key={item} className="rounded-md border border-emerald-400/10 bg-emerald-400/[0.045] px-2 py-1.5 text-[10px] text-emerald-100/75">{item}</span>)}
        </div>
      </div>
    ),
  },
];

export default function Features() {
  const { ref, inView } = useScrollReveal(0.08);

  return (
    <section id="features" className="relative py-16 md:py-20 lg:py-24 overflow-hidden" ref={ref}>
      <div
        className="glow-orb w-[500px] h-[500px] -left-48 top-1/2 -translate-y-1/2 opacity-[0.07]"
        style={{ background: "radial-gradient(ellipse, #6366F1, transparent)" }}
        aria-hidden="true"
      />

      <div className="container relative z-10">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
          className="text-center mb-14"
        >
          <motion.div variants={staggerItem}>
            <span className="badge-pill mb-5">Five connected specialists</span>
          </motion.div>
          <motion.h2
            variants={staggerItem}
            className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-5 tracking-tight"
            style={{ fontFamily: "'Outfit', sans-serif" }}
          >
            A specialist for every signal. <span className="gradient-text">Evidence in every conclusion.</span>
          </motion.h2>
          <motion.p variants={staggerItem} className="text-white/65 text-lg max-w-2xl mx-auto leading-relaxed">
            Three domain agents inspect the submitted telemetry. Correlation and reporting connect their findings into one reviewable diagnosis.
          </motion.p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <motion.div
            initial={{ opacity: 0, y: 36 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.65, delay: 0.1 }}
            className="lg:col-span-2 gradient-border rounded-2xl overflow-hidden card-hover"
          >
            <div className="p-7 pb-5">
              <div className="flex items-start gap-4 mb-5">
                <div className="w-10 h-10 rounded-xl border flex items-center justify-center flex-shrink-0 bg-indigo-500/10 border-indigo-500/20">
                  <Activity className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-white font-semibold text-lg mb-1" style={{ fontFamily: "'Outfit', sans-serif" }}>
                    Telemetry & Performance
                  </h3>
                  <p className="text-white/65 text-sm leading-relaxed">
                    Checks latency, jitter, packet loss, throughput and link utilization from the data you provide.
                  </p>
                </div>
              </div>
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
                <div className="text-[11px] font-mono uppercase tracking-[0.16em] text-indigo-300/70 mb-4">Performance signals analyzed</div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {["Latency", "Jitter", "Packet loss", "Throughput", "Link use"].map((signal) => (
                    <div key={signal} className="rounded-lg border border-white/[0.06] bg-[#08080F] px-3 py-3 text-center text-xs text-white/65">{signal}</div>
                  ))}
                </div>
                <svg viewBox="0 0 640 74" className="w-full h-14 mt-4 opacity-80" preserveAspectRatio="none" aria-label="Decorative, illustrative signal trace">
                  <defs><linearGradient id="signal-glow" x1="0" x2="1"><stop offset="0" stopColor="#6366f1" stopOpacity=".15" /><stop offset=".5" stopColor="#a78bfa" stopOpacity=".8" /><stop offset="1" stopColor="#6366f1" stopOpacity=".18" /></linearGradient></defs>
                  <path d="M0 48 C40 48 42 35 75 35 S115 52 151 48 S188 41 214 42 S249 18 280 22 S322 54 354 46 S399 35 427 39 S461 57 489 49 S526 20 556 28 S601 48 640 27" fill="none" stroke="url(#signal-glow)" strokeWidth="2" />
                  <path d="M0 61 H640" fill="none" stroke="rgba(255,255,255,.06)" strokeWidth="1" strokeDasharray="3 6" />
                </svg>
                <p className="text-white/35 text-xs mt-1">Illustrative signal trace · analysis uses submitted telemetry, not background monitoring.</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 36 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.65, delay: 0.18 }}
            className="gradient-border rounded-2xl overflow-hidden card-hover flex flex-col"
          >
            <div className="p-7 flex flex-col flex-1">
              <div className="flex items-start gap-4 mb-5">
                <div className="w-10 h-10 rounded-xl border flex items-center justify-center flex-shrink-0 bg-cyan-500/10 border-cyan-500/20">
                  <Cpu className="w-5 h-5 text-cyan-300" />
                </div>
                <div>
                  <h3 className="text-white font-semibold text-lg mb-1" style={{ fontFamily: "'Outfit', sans-serif" }}>
                    Infrastructure Health
                  </h3>
                  <p className="text-white/65 text-sm leading-relaxed">
                    Reviews device resources, interface errors, queue drops and reported status.
                  </p>
                </div>
              </div>
              <div className="flex-1 rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 flex flex-col justify-center gap-3">
                {["CPU & memory", "Interface errors", "Egress queue drops", "Device status"].map((signal, index) => (
                  <div key={signal} className="flex items-center gap-3 rounded-lg bg-[#08080F] border border-white/[0.05] px-3 py-2.5">
                    <span className={`w-2 h-2 rounded-full ${index === 0 ? "bg-violet-400" : "bg-indigo-400/70"}`} />
                    <span className="text-xs text-white/65">{signal}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {supportingAgents.map((agent, index) => (
            <motion.div
              key={agent.title}
              initial={{ opacity: 0, y: 36 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.65, delay: 0.26 + index * 0.08 }}
              className="gradient-border rounded-2xl p-7 card-hover group"
            >
              <div className={`w-10 h-10 rounded-xl border flex items-center justify-center mb-5 transition-colors duration-300 ${agent.iconBg}`}>
                {agent.icon}
              </div>
              <h3 className="text-white font-semibold text-base mb-2.5" style={{ fontFamily: "'Outfit', sans-serif" }}>
                {agent.title}
              </h3>
              <p className="text-white/65 text-sm leading-relaxed">{agent.desc}</p>
              {agent.visual}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
