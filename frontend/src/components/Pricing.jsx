import { motion } from "framer-motion";
import { Activity, Braces, Check, Cpu, FileText, GitBranch, Network, ShieldCheck } from "lucide-react";
import { useScrollReveal, staggerContainer, staggerItem } from "@/hooks/useScrollReveal";

const stages = ["Performance", "Infrastructure", "Connectivity", "Correlation", "Reporting"];

export default function Pricing() {
  const { ref, inView } = useScrollReveal(0.08);

  return (
    <section id="pricing" className="relative py-16 md:py-20 lg:py-24 overflow-hidden" ref={ref}>
      <div className="section-divider absolute top-0 left-0 right-0" />
      <div className="glow-orb w-[700px] h-[500px] left-1/2 -translate-x-1/2 bottom-0 opacity-[0.07]" style={{ background: "radial-gradient(ellipse, #6366F1, transparent)" }} aria-hidden="true" />

      <div className="container relative z-10">
        <motion.div variants={staggerContainer} initial="hidden" animate={inView ? "visible" : "hidden"} className="text-center mb-14">
          <motion.div variants={staggerItem}><span className="badge-pill mb-5">Platform capabilities</span></motion.div>
          <motion.h2 variants={staggerItem} className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-5 tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>
            From network signals to <span className="gradient-text">useful next steps.</span>
          </motion.h2>
          <motion.p variants={staggerItem} className="text-white/65 text-lg max-w-2xl mx-auto">
            One validated request coordinates analysis and returns a result your team can inspect.
          </motion.p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3 auto-rows-fr">
          <motion.article initial={{ opacity: 0, y: 28 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: .6, delay: .08 }} className="capability-bento capability-bento--signals lg:col-span-3 lg:row-span-2 gradient-border rounded-2xl p-7 md:p-8 card-hover overflow-hidden">
            <div className="flex items-center gap-3 mb-4"><span className="capability-icon"><Activity size={19} /></span><span className="capability-kicker">01 / Input coverage</span></div>
            <h3 className="text-white font-semibold text-2xl mb-2" style={{ fontFamily: "'Outfit', sans-serif" }}>Bring three network domains together.</h3>
            <p className="text-white/60 text-sm leading-relaxed max-w-lg">Performance measurements, infrastructure health and connectivity topology enter one diagnosis with a shared ID.</p>
            <div className="capability-signal-map mt-7">
              <div className="capability-signal-map__source"><Activity size={16} /><span>Performance</span></div>
              <div className="capability-signal-map__source"><Cpu size={16} /><span>Infrastructure</span></div>
              <div className="capability-signal-map__source"><Network size={16} /><span>Connectivity</span></div>
              <span className="capability-signal-map__line capability-signal-map__line--one" />
              <span className="capability-signal-map__line capability-signal-map__line--two" />
              <span className="capability-signal-map__line capability-signal-map__line--three" />
              <div className="capability-signal-map__target"><GitBranch size={17} /><span>Shared diagnosis</span></div>
            </div>
            <p className="mt-4 text-[10px] text-white/35">Inputs are provided by the operator; NetCoop does not poll devices.</p>
          </motion.article>

          <motion.article initial={{ opacity: 0, y: 28 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: .6, delay: .16 }} className="capability-bento capability-bento--flow lg:col-span-3 gradient-border rounded-2xl p-7 card-hover overflow-hidden">
            <div className="flex items-center gap-3 mb-3"><span className="capability-icon capability-icon--violet"><GitBranch size={18} /></span><span className="capability-kicker">02 / Coordinated analysis</span></div>
            <h3 className="text-white font-semibold text-xl mb-2" style={{ fontFamily: "'Outfit', sans-serif" }}>Five stages, with clear handoffs.</h3>
            <p className="text-white/60 text-sm">Three domain agents feed correlation and reporting.</p>
            <div className="capability-stage-flow mt-5">
              {stages.map((stage, index) => <div className="capability-stage" key={stage}><span>0{index + 1}</span><b>{stage}</b>{index < stages.length - 1 && <i aria-hidden="true">→</i>}</div>)}
            </div>
          </motion.article>

          <motion.article initial={{ opacity: 0, y: 28 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: .6, delay: .22 }} className="capability-bento lg:col-span-2 gradient-border rounded-2xl p-6 card-hover">
            <span className="capability-icon capability-icon--violet mb-4"><ShieldCheck size={18} /></span>
            <h3 className="text-white font-semibold text-lg mb-2" style={{ fontFamily: "'Outfit', sans-serif" }}>Evidence stays attached.</h3>
            <p className="text-white/55 text-sm mb-4">Inspect which agent finding supports each correlated hypothesis.</p>
            <div className="capability-evidence-row"><span>Agent finding</span><b>→</b><span>Evidence reference</span></div>
          </motion.article>

          <motion.article initial={{ opacity: 0, y: 28 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: .6, delay: .28 }} className="capability-bento lg:col-span-2 gradient-border rounded-2xl p-6 card-hover">
            <span className="capability-icon mb-4"><Check size={18} /></span>
            <h3 className="text-white font-semibold text-lg mb-2" style={{ fontFamily: "'Outfit', sans-serif" }}>Partial outcomes stay visible.</h3>
            <p className="text-white/55 text-sm mb-4">A failed stage is reported as such; no findings are invented to fill the gap.</p>
            <div className="capability-state-row"><span className="capability-state capability-state--done">Completed</span><span className="capability-state capability-state--failed">Failed stage</span></div>
          </motion.article>

          <motion.article initial={{ opacity: 0, y: 28 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: .6, delay: .34 }} className="capability-bento lg:col-span-2 gradient-border rounded-2xl p-6 card-hover">
            <span className="capability-icon capability-icon--violet mb-4"><Braces size={18} /></span>
            <h3 className="text-white font-semibold text-lg mb-2" style={{ fontFamily: "'Outfit', sans-serif" }}>Structured, reviewable output.</h3>
            <p className="text-white/55 text-sm mb-4">Agent messages, correlation results and diagnostic reports retain their API shape.</p>
            <div className="capability-json"><span>{"{ "}</span>agent_messages<span>, correlation_result, diagnostic_report {"}"}</span></div>
          </motion.article>
        </div>
      </div>
    </section>
  );
}
