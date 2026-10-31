import { ArrowLeft, Network } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#030305] text-white px-6 py-12 text-center">
      <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-6 shadow-lg shadow-indigo-500/20">
        <Network size={24} />
      </div>
      <h1 className="text-4xl font-bold mb-3" style={{ fontFamily: "'Outfit', sans-serif" }}>
        Page Not Found
      </h1>
      <p className="text-white/60 max-w-md mb-8">
        The requested network diagnostic route does not exist or has been moved.
      </p>
      <a
        href="/"
        className="btn-primary inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white"
      >
        <ArrowLeft size={16} />
        Return to Home
      </a>
    </div>
  );
}
