import { motion } from "framer-motion";
import { Activity, AlertTriangle, ArrowRight, Check, FileText, ShieldCheck } from "lucide-react";
import { useScrollReveal, staggerContainer, staggerItem } from "@/hooks/useScrollReveal";

export default function EvidencePreview() {
  const { ref, inView } = useScrollReveal(0.08);

  return (
    <section id="evidence" className="relative py-16 md:py-20 lg:py-24 overflow-hidden" ref={ref}>
      <div className="section-divider absolute top-0 left-0 right-0" />
      <div className="glow-orb w-[680px] h-[460px] right-[-12rem] top-1/3 opacity-[0.07]" style={{ background: "radial-gradient(ellipse, #8B5CF6, transparent)" }} aria-hidden="true" />

      <div className="container relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-[.55fr_1.45fr] gap-8 lg:gap-10 items-center">
          <motion.div variants={staggerContainer} initial="hidden" animate={inView ? "visible" : "hidden"}>
            <motion.span variants={staggerItem} className="badge-pill mb-5"><FileText size={13} /> REPORT PREVIEW</motion.span>
            <motion.h2 variants={staggerItem} className="text-4xl md:text-5xl font-bold text-white tracking-tight leading-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>
              See the evidence behind <span className="gradient-text">the diagnosis.</span>
            </motion.h2>
            <motion.p variants={staggerItem} className="text-white/60 text-base leading-relaxed mt-5 max-w-lg">
              The report links a probable cause to findings from separate agents and carries uncertainty into the recommended next checks.
            </motion.p>
            <motion.div variants={staggerItem} className="mt-7 flex items-center gap-3 text-xs text-white/45">
              <span className="w-8 h-8 rounded-xl border border-indigo-400/15 bg-indigo-500/10 flex items-center justify-center text-indigo-300"><ShieldCheck size={16} /></span>
              Example only · values are not live network telemetry
            </motion.div>
          </motion.div>

          <motion.article initial={{ opacity: 0, y: 24, scale: .985 }} animate={inView ? { opacity: 1, y: 0, scale: 1 } : {}} transition={{ duration: .65, delay: .12 }} className="sample-report gradient-border rounded-2xl overflow-hidden">
            <header className="sample-report__header">
              <div className="flex items-center gap-3"><span className="sample-report__icon"><FileText size={17} /></span><div><span className="sample-report__eyebrow">DIAGNOSTIC REPORT</span><strong>Network congestion</strong></div></div>
              <span className="sample-report__sample"><i /> ILLUSTRATIVE SAMPLE</span>
            </header>

            <div className="p-5 md:p-8">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
                <span className="sample-report__id">EXAMPLE · scenario-congestion-002</span>
                <span className="sample-report__status"><span /> PROBABLE CAUSE</span>
              </div>

              <div className="sample-report__cause">
                <div><span className="sample-report__label">PROBABLE ROOT CAUSE</span><p>Reported interface errors or egress queue drops coincide with packet loss on the same device and may be contributing.</p></div>
                <div className="sample-report__confidence"><span>CONFIDENCE</span><strong>Moderate</strong><small>Heuristic category</small></div>
              </div>

              <div className="sample-report__section-title"><span>SUPPORTING EVIDENCE</span><span>2 agent references</span></div>
              <div className="sample-report__evidence-list">
                <div className="sample-report__evidence"><span className="sample-report__evidence-icon sample-report__evidence-icon--blue"><Activity size={15} /></span><div><span>PERFORMANCE · packet loss</span><strong>2.4% reported</strong><small>RTR-C2 · xe-0/0/1</small></div><Check size={15} /></div>
                <div className="sample-report__evidence"><span className="sample-report__evidence-icon sample-report__evidence-icon--violet"><AlertTriangle size={15} /></span><div><span>INFRASTRUCTURE · egress queue drops</span><strong>18 drops reported</strong><small>RTR-C2 · xe-0/0/1</small></div><Check size={15} /></div>
              </div>

              <div className="sample-report__action">
                <div className="sample-report__section-title"><span>RECOMMENDED NEXT CHECK</span><ArrowRight size={14} /></div>
                <p>Inspect interface error and egress queue counters on the cited device and interface for the same measurement window. Verify queue configuration before changing traffic handling.</p>
              </div>

              <p className="sample-report__disclaimer">Confidence categories use a deterministic heuristic; they are not calibrated probabilities. This is an illustrative report preview, not a live diagnosis.</p>
            </div>
          </motion.article>
        </div>
      </div>
    </section>
  );
}
