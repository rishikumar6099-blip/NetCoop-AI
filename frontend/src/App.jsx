import { lazy, Suspense, useState } from "react";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { DiagnosisRunContext } from "./contexts/DiagnosisContext";
import Home from "./pages/Home";
import NotFound from "./pages/NotFound";

const Dashboard = lazy(() => import("./Dashboard.jsx"));

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/dashboard" component={Dashboard} />
      <Route path="/dashboard/analytics" component={Dashboard} />
      <Route path="/dashboard/infrastructure" component={Dashboard} />
      <Route path="/dashboard/agents" component={Dashboard} />
      <Route path="/dashboard/communication" component={Dashboard} />
      <Route path="/dashboard/interop" component={Dashboard} />
      <Route path="/dashboard/diagnose" component={Dashboard} />
      <Route path="/dashboard/reports" component={Dashboard} />
      <Route path="/404" component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

export default function App() {
  const [diagnosisRun, setDiagnosisRun] = useState(null);
  const dashboardFallback = (
    <div className="min-h-screen bg-[#030305] px-6 py-12 text-center text-white/65 flex items-center justify-center">
      <div className="flex items-center gap-3">
        <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-ping" />
        <span style={{ fontFamily: "'Outfit', sans-serif" }}>Opening Network Operations…</span>
      </div>
    </div>
  );

  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="dark">
        <DiagnosisRunContext.Provider value={{ diagnosisRun, setDiagnosisRun }}>
          <Suspense fallback={dashboardFallback}>
            <Router />
          </Suspense>
        </DiagnosisRunContext.Provider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
