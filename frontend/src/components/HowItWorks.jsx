import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Activity, Cpu, FileText, GitBranch, Network } from "lucide-react";
import { useScrollReveal, staggerContainer, staggerItem } from "@/hooks/useScrollReveal";

function useCountUp(target, inView, duration = 1800) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const step = target / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= target) { setCount(target); clearInterval(timer); }
      else setCount(Math.floor(start));
    }, 16);
    return () => clearInterval(timer);
  }, [inView, target, duration]);
  return count;
}

const stats = [
  { value: 5, suffix: "", label: "Specialist stages", decimals: 0 },
  { value: 3, suffix: "", label: "Domain analyses", decimals: 0 },
  { value: 1, suffix: "", label: "Shared diagnosis ID", decimals: 0 },
  { value: 2, suffix: "", label: "Possible result states", decimals: 0 },
];

function StatCard({ stat, inView, delay }) {
  const raw = useCountUp(stat.value * (stat.decimals ? 10 : 1), inView);
  const display = stat.decimals ? (raw / 10).toFixed(stat.decimals) : raw;
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.55, delay }}
      className="gradient-border rounded-2xl p-5 text-center"
    >
      <div
        className="text-3xl font-bold gradient-text mb-1"
        style={{ fontFamily: "'Outfit', sans-serif" }}
      >
        {display}{stat.suffix}
      </div>
      <div className="text-white/55 text-xs leading-snug">{stat.label}</div>
    </motion.div>
  );
}

const steps = [
  {
    number: "01",
    icon: <Activity className="w-5 h-5 text-indigo-400" />,
    iconBg: "bg-indigo-500/10 border-indigo-500/20",
    title: "Telemetry & Performance",
    desc: "Inspects latency, jitter, packet loss, throughput and link utilization in the submitted samples.",
    detail: "Findings are tied to the source device and interface when provided.",
  },
  {
    number: "02",
    icon: <Cpu className="w-5 h-5 text-violet-400" />,
    iconBg: "bg-violet-500/10 border-violet-500/20",
    title: "Infrastructure Health",
    desc: "Reviews device resources, interface errors, queue drops and reported device state.",
    detail: "Resource and interface findings are compared with performance signals.",
  },
  {
    number: "03",
    icon: <Network className="w-5 h-5 text-indigo-400" />,
    iconBg: "bg-indigo-500/10 border-indigo-500/20",
    title: "Connectivity Analysis",
    desc: "Checks supplied devices, links, reachability and network segments to understand incident scope.",
    detail: "The agent reasons only from the topology and status you submit.",
  },
  {
    number: "04",
    icon: <GitBranch className="w-5 h-5 text-violet-400" />,
    iconBg: "bg-violet-500/10 border-violet-500/20",
    title: "Fault Correlation",
    desc: "Compares specialist findings and ranks evidence-supported root-cause hypotheses.",
    detail: "Alternative explanations, conflicts and uncertainty remain visible.",
  },
  {
    number: "05",
    icon: <FileText className="w-5 h-5 text-indigo-400" />,
    iconBg: "bg-indigo-500/10 border-indigo-500/20",
    title: "Recommendation & Reporting",
    desc: "Builds the unified report with confidence category, evidence and recommended checks.",
    detail: "Failed stages are returned as partial results rather than synthesized findings.",
  },
];

export default function HowItWorks() {
  const { ref, inView } = useScrollReveal(0.08);

  return (
    <section id="how-it-works" className="relative py-16 md:py-20 lg:py-24 overflow-hidden" ref={ref}>
      <div className="section-divider absolute top-0 left-0 right-0" />

      <div
        className="glow-orb w-[500px] h-[500px] -right-48 top-1/2 -translate-y-1/2 opacity-[0.07]"
        style={{ background: "radial-gradient(ellipse, #8B5CF6, transparent)" }}
        aria-hidden="true"
      />

      <div className="container relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-10 lg:gap-14 items-start">
          {/* Left: sticky header + stats */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            className="lg:sticky lg:top-28"
          >
            <motion.div variants={staggerItem}>
              <span className="badge-pill mb-5">Five-stage workflow</span>
            </motion.div>
            <motion.h2
              variants={staggerItem}
              className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 tracking-tight leading-tight"
              style={{ fontFamily: "'Outfit', sans-serif" }}
            >
              Five stages. <span className="gradient-text">One diagnosis.</span>
            </motion.h2>
            <motion.p variants={staggerItem} className="text-white/65 text-lg leading-relaxed mb-10">
              Each agent contributes a distinct analysis. Directional handoffs keep the route from source telemetry to report easy to follow.
            </motion.p>

            {/* Count-up stats */}
            <div className="grid grid-cols-2 gap-3">
              {stats.map((stat, i) => (
                <StatCard key={stat.label} stat={stat} inView={inView} delay={0.3 + i * 0.08} />
              ))}
            </div>
          </motion.div>

          {/* Right: steps */}
          <div className="flex flex-col">
            {steps.map((step, i) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, x: 28 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.65, delay: 0.2 + i * 0.18 }}
                className="workflow-stage relative flex gap-5 pb-9 last:pb-0 group"
              >
                {/* Animated connector line */}
                {i < steps.length - 1 && (
                  <motion.div
                    className="workflow-stage__connector absolute left-5 top-14 bottom-0 w-px step-line"
                    initial={{ scaleY: 0, originY: 0 }}
                    animate={inView ? { scaleY: 1 } : {}}
                    transition={{ duration: 0.8, delay: 0.5 + i * 0.18 }}
                    aria-hidden="true"
                  />
                )}

                {/* Step icon */}
                <div className={`flex-shrink-0 w-10 h-10 rounded-xl border flex items-center justify-center mt-0.5 transition-all duration-300 group-hover:scale-110 ${step.iconBg}`}>
                  {step.icon}
                </div>

                {/* Step content */}
                <div className="flex-1 pt-1">
                  <div className="flex items-center gap-3 mb-3">
                    <span
                      className="text-xs font-mono text-white/50 tracking-[0.15em]"
                      style={{ fontFamily: "'Fira Code', monospace" }}
                    >
                      {step.number}
                    </span>
                    <div className="h-px flex-1 bg-white/[0.05]" />
                  </div>
                  <h3
                    className="text-xl font-semibold text-white mb-3 leading-snug"
                    style={{ fontFamily: "'Outfit', sans-serif" }}
                  >
                    {step.title}
                  </h3>
                  <p className="text-white/65 leading-relaxed mb-3 text-[0.95rem]">{step.desc}</p>
                  <p className="text-sm text-indigo-300/60 italic leading-relaxed">{step.detail}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
