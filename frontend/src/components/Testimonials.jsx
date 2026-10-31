import { motion } from "framer-motion";
import { Braces, CheckCircle2, GitBranch, SearchCheck } from "lucide-react";
import { useScrollReveal, staggerContainer, staggerItem } from "@/hooks/useScrollReveal";

const principles = [
  {
    icon: SearchCheck,
    title: "Evidence-based diagnosis",
    text: "Every cause stays connected to the specialist findings that support it.",
    visual: <div className="principle-evidence-flow"><span>Source signal</span><b>→</b><span>Agent finding</span><b>→</b><span>Cause</span></div>,
  },
  {
    icon: GitBranch,
    title: "Uncertainty handled openly",
    text: "Confidence is a category, while conflicts and limitations remain visible for review.",
    visual: <div className="principle-uncertainty"><span className="principle-chip principle-chip--supported">Supported</span><span className="principle-chip principle-chip--uncertain">Uncertain</span><span className="principle-chip principle-chip--conflict">Conflict</span></div>,
  },
  {
    icon: CheckCircle2,
    title: "Partial results are honest",
    text: "Completed messages and failed stages are returned explicitly without fabricated findings.",
    visual: <div className="principle-stage-state"><small>ILLUSTRATIVE STAGE STATE</small><span><i />Domain agents completed</span><b>Partial result</b><span><i />Fault correlation failed</span></div>,
  },
  {
    icon: Braces,
    title: "Explainable output",
    text: "Review the diagnosis ID, source references, alternatives and recommended checks together.",
    visual: <div className="principle-report-lines"><span /><span /><span /><span /></div>,
  },
];

export default function Testimonials() {
  const { ref, inView } = useScrollReveal(0.08);

  return (
    <section id="testimonials" className="relative py-16 md:py-20 lg:py-24 overflow-hidden" ref={ref}>
      <div className="section-divider absolute top-0 left-0 right-0" />
      <div className="glow-orb w-[900px] h-[400px] left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 opacity-[0.05]" style={{ background: "radial-gradient(ellipse, rgba(99,102,241,0.8), transparent)" }} aria-hidden="true" />

      <div className="container relative z-10">
        <motion.div variants={staggerContainer} initial="hidden" animate={inView ? "visible" : "hidden"} className="text-center mb-12">
          <motion.div variants={staggerItem}><span className="badge-pill mb-5">Evidence you can inspect</span></motion.div>
          <motion.h2 variants={staggerItem} className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-5 tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>
            Clear conclusions, <span className="gradient-text">with their reasoning.</span>
          </motion.h2>
          <motion.p variants={staggerItem} className="text-white/65 text-lg max-w-2xl mx-auto">
            Review what the system found, what it could not establish and where each conclusion came from.
          </motion.p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {principles.map(({ icon: Icon, title, text, visual }, index) => (
            <motion.article key={title} initial={{ opacity: 0, y: 26 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: .58, delay: .1 + index * .08 }} className="principle-card gradient-border rounded-2xl p-6 md:p-7 card-hover">
              <div className="flex items-start justify-between gap-4">
                <div><span className="principle-card__icon"><Icon size={19} /></span><h3 className="text-white font-semibold text-lg mt-4 mb-2" style={{ fontFamily: "'Outfit', sans-serif" }}>{title}</h3><p className="text-white/55 text-sm leading-relaxed max-w-md">{text}</p></div>
                <span className="principle-card__index">0{index + 1}</span>
              </div>
              {visual}
            </motion.article>
          ))}
        </div>

        <motion.div initial={{ opacity: 0, y: 14 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: .5, delay: .45 }} className="principle-legend mt-5">
          <span><i className="principle-dot principle-dot--complete" /> Complete · all stages returned</span>
          <span><i className="principle-dot principle-dot--partial" /> Partial · failed stage preserved</span>
          <span><i className="principle-dot principle-dot--evidence" /> Evidence · references stay attached</span>
        </motion.div>
      </div>
    </section>
  );
}
