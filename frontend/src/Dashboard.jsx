import { useContext, useEffect, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3,
  Check, ChevronDown, CircleHelp, Clock3, Cpu, FileJson, FileText, Gauge,
  GitBranch, HardDrive, LayoutDashboard, Menu, Network, Radio, ScanSearch,
  Server, ShieldCheck, Sparkles, Waypoints, Wifi, X, Zap,
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { useLocation } from 'wouter'
import { DiagnosisRunContext } from './contexts/DiagnosisContext'
import DiagnosisForm from './components/DiagnosisForm.jsx'
import './Dashboard.css'

const navigation = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, group: 'OPERATIONS' },
  { id: 'analytics', label: 'Network Analytics', icon: BarChart3, group: 'OPERATIONS' },
  { id: 'infrastructure', label: 'Infrastructure', icon: Server, group: 'OPERATIONS' },
  { id: 'agents', label: 'AI Agents', icon: Sparkles, group: 'INTELLIGENCE' },
  { id: 'communication', label: 'Agent Communication', icon: Waypoints, group: 'INTELLIGENCE' },
  { id: 'diagnosis', label: 'Run Diagnosis', icon: ScanSearch, group: 'DIAGNOSE' },
  { id: 'reports', label: 'Diagnostic Reports', icon: FileText, group: 'DIAGNOSE' },
]

const pagePaths = {
  overview: '/dashboard',
  analytics: '/dashboard/analytics',
  infrastructure: '/dashboard/infrastructure',
  agents: '/dashboard/agents',
  communication: '/dashboard/communication',
  diagnosis: '/dashboard/diagnose',
  reports: '/dashboard/reports',
}
const pathPages = Object.fromEntries(
  Object.entries(pagePaths).map(([page, path]) => [path, page]),
)

const agents = [
  { id: '01', name: 'Telemetry & Performance', icon: Activity, tone: 'blue', role: 'Performance signals', description: 'Evaluates latency, jitter, packet loss, throughput and link utilization.', focus: ['Latency', 'Jitter', 'Packet loss'], stage: 'performance' },
  { id: '02', name: 'Infrastructure Health', icon: Cpu, tone: 'cyan', role: 'Device condition', description: 'Reviews resource pressure, interface errors, queue drops and device status.', focus: ['CPU & memory', 'Errors', 'Queue drops'], stage: 'infrastructure' },
  { id: '03', name: 'Connectivity Analysis', icon: Network, tone: 'violet', role: 'Topology and scope', description: 'Checks supplied reachability, links, network segments and impact scope.', focus: ['Reachability', 'Links', 'Segments'], stage: 'connectivity' },
  { id: '04', name: 'Fault Correlation', icon: GitBranch, tone: 'blue', role: 'Evidence correlation', description: 'Compares findings, weighs alternatives and preserves conflicting evidence.', focus: ['Evidence refs', 'Alternatives', 'Confidence'], stage: 'fault_correlation' },
  { id: '05', name: 'Recommendation & Reporting', icon: FileText, tone: 'cyan', role: 'Unified output', description: 'Creates the evidence-linked report, limitations and practical next steps.', focus: ['Root cause', 'Limitations', 'Actions'], stage: 'recommendation_reporting' },
]

const latencyData = [
  { time: '00:00', latency: 24 }, { time: '04:00', latency: 27 },
  { time: '08:00', latency: 23 }, { time: '12:00', latency: 35 },
  { time: '16:00', latency: 29 }, { time: '20:00', latency: 31 },
  { time: '24:00', latency: 25 },
]
const trafficData = [
  { time: '00:00', inbound: 42, outbound: 28 }, { time: '04:00', inbound: 35, outbound: 24 },
  { time: '08:00', inbound: 61, outbound: 43 }, { time: '12:00', inbound: 78, outbound: 58 },
  { time: '16:00', inbound: 68, outbound: 51 }, { time: '20:00', inbound: 55, outbound: 39 },
  { time: '24:00', inbound: 46, outbound: 31 },
]
const deviceHealth = [
  { name: 'Healthy', value: 231, color: '#51d5b4' },
  { name: 'Degraded', value: 13, color: '#63b8ff' },
  { name: 'Attention', value: 4, color: '#eab26c' },
]
const activityRows = [
  { id: 'DGN-014', severity: 'High', tone: 'high', title: 'Elevated packet loss on edge router', cause: 'Queue drops may be contributing', device: 'RTR-EDGE-04', time: '14:32:08' },
  { id: 'DGN-013', severity: 'Medium', tone: 'medium', title: 'Intermittent latency in branch segment', cause: 'Resource pressure is a possibility', device: 'RTR-BRANCH-12', time: '13:48:26' },
  { id: 'DGN-012', severity: 'Low', tone: 'low', title: 'Connectivity scope review', cause: 'No single cause established', device: 'SEG-WEST-02', time: '12:16:51' },
  { id: 'DGN-011', severity: 'Info', tone: 'info', title: 'Routine network assessment', cause: 'No fault detected', device: 'CORE-NET-01', time: '10:04:13' },
]
const infrastructureRows = [
  { device: 'RTR-CORE-01', role: 'Core router', cpu: 42, memory: 61, errors: 0, drops: 0, status: 'Online', tone: 'healthy' },
  { device: 'RTR-EDGE-04', role: 'Edge router', cpu: 78, memory: 73, errors: 8, drops: 18, status: 'Degraded', tone: 'review' },
  { device: 'SW-DIST-08', role: 'Distribution switch', cpu: 31, memory: 48, errors: 0, drops: 0, status: 'Online', tone: 'healthy' },
  { device: 'RTR-BRANCH-12', role: 'Branch router', cpu: 66, memory: 82, errors: 2, drops: 3, status: 'Degraded', tone: 'degraded' },
]

const demoMessages = [
  { key: 'performance', label: 'Performance Agent', stage: 'DOMAIN ANALYSIS', message: { schema_version: '1.0', diagnosis_id: 'illustrative-example', agent: 'performance', summary: 'Illustrative message shape. Values below are sample content, not a live diagnosis.', samples_analyzed: 1, findings: [{ metric: 'latency', value: 24, unit: 'ms', severity: 'info', assessment: 'Example finding for interface preview only.' }] } },
  { key: 'infrastructure', label: 'Infrastructure Agent', stage: 'DOMAIN ANALYSIS', message: { schema_version: '1.0', diagnosis_id: 'illustrative-example', agent: 'infrastructure', summary: 'Illustrative message shape. Values below are sample content, not a live diagnosis.', samples_analyzed: 1, findings: [{ metric: 'CPU utilisation', value: 42, unit: '%', severity: 'info', device_id: 'SAMPLE-DEVICE', assessment: 'Example finding for interface preview only.' }] } },
  { key: 'connectivity', label: 'Connectivity Agent', stage: 'DOMAIN ANALYSIS', message: { schema_version: '1.0', diagnosis_id: 'illustrative-example', agent: 'connectivity', summary: 'Illustrative message shape. Values below are sample content, not a live diagnosis.', samples_analyzed: 1, findings: [] } },
]

const titles = {
  overview: 'Overview', analytics: 'Network analytics', infrastructure: 'Infrastructure',
  agents: 'AI agent roster', communication: 'Agent communication', diagnosis: 'Run a diagnosis', reports: 'Diagnostic reports',
}

function DemoFlag({ compact = false }) { return <span className={`demo-flag${compact ? ' demo-flag--compact' : ''}`}><i /> Illustrative data</span> }

function Sidebar({ activePage, onNavigate, open, onClose, apiStatus }) {
  const groups = [...new Set(navigation.map((item) => item.group))]
  return <>
    {open && <button aria-label="Close navigation" className="nav-scrim" onClick={onClose} type="button" />}
    <aside className={`nav-rail${open ? ' nav-rail--open' : ''}`}>
      <div className="nav-rail__brand"><a className="ops-brand" href="/"><span className="ops-brand__mark"><Network size={19} /><i /></span><span>netcoop<span>ai</span></span></a><button className="nav-rail__close" aria-label="Close navigation" onClick={onClose} type="button"><X size={19} /></button></div>
      <div className="workspace-switch"><span><Network size={16} /></span><div><b>Network operations</b><small>Prototype workspace</small></div><ChevronDown size={15} /></div>
      <nav className="nav-groups" aria-label="Dashboard navigation">{groups.map((group) => <div className="nav-group" key={group}><span className="nav-group__label">{group}</span>{navigation.filter((item) => item.group === group).map(({ id, label, icon: Icon }) => <button key={id} type="button" aria-current={activePage === id ? 'page' : undefined} className={`nav-link${activePage === id ? ' nav-link--active' : ''}`} onClick={() => { onNavigate(id); onClose() }}><Icon size={18} strokeWidth={1.8} /><span>{label}</span>{id === 'diagnosis' && <i className="nav-link__new">NEW</i>}</button>)}</div>)}</nav>
      <div className="nav-rail__bottom"><div className="api-state"><span className={`api-state__icon api-state__icon--${apiStatus.tone}`}><Radio size={16} /></span><div><b>Diagnosis API</b><small><i className={`state-dot state-dot--${apiStatus.tone}`} />{apiStatus.label}</small></div><CircleHelp size={15} /></div><div className="nav-rail__foot"><span>NETCOOP AI</span><span>OPS / 01</span></div></div>
    </aside>
  </>
}

function Topbar({ title, time, apiStatus, onMenu, onDiagnosis }) {
  return <header className="ops-topbar"><button className="ops-topbar__menu" onClick={onMenu} aria-label="Open navigation" type="button"><Menu size={19} /></button><div className="ops-topbar__heading"><span>NETWORK OPERATIONS CENTER</span><h1>{title}</h1></div><div className="ops-topbar__tools"><span className={`topbar-status topbar-status--${apiStatus.tone}`}><i />{apiStatus.label}</span><span className="topbar-separator" /><span className="ops-clock"><Clock3 size={15} />{time}</span><button className="topbar-run" type="button" onClick={onDiagnosis}><ScanSearch size={16} /> New diagnosis</button><span className="operator-avatar">OP</span></div></header>
}

function PageHeader({ kicker, title, description, action }) {
  return <div className="page-heading"><div><div className="page-heading__kicker">{kicker}</div><h2>{title}</h2><p>{description}</p></div>{action && <div className="page-heading__action">{action}</div>}</div>
}

function SampleBanner({ children = 'Illustrative sample data · these values are not live network telemetry.' }) {
  return <div className="sample-banner"><span><Activity size={17} /></span><p><b>Visual sample</b>{' '}{children}</p><DemoFlag compact /></div>
}

function KpiCard({ icon: Icon, label, value, unit, note, tone = 'blue', trend }) {
  return <article className={`kpi-card kpi-card--${tone}`}><div className="kpi-card__top"><span><Icon size={18} /></span><small>{label}</small><ArrowUpRight size={15} /></div><div className="kpi-card__number">{value}<i>{unit}</i></div><div className="kpi-card__bottom"><span>{note}</span>{trend && <b>{trend}</b>}</div><div className="kpi-card__glow" /></article>
}

function Panel({ title, subtitle, action, className = '', children }) {
  return <section className={`surface-panel ${className}`}><header className="surface-panel__header"><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>{action}</header>{children}</section>
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return <div className="ops-chart-tooltip"><span>{label}</span>{payload.map((item) => <b key={item.dataKey} style={{ '--series-color': item.color }}>{item.name}: {item.value}{item.dataKey === 'latency' ? ' ms' : item.dataKey.includes('bound') ? ' Mbps' : ''}</b>)}</div>
}

function LatencyChart() {
  return <div className="ops-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={latencyData} margin={{ top: 13, right: 12, left: -18, bottom: 0 }}><CartesianGrid stroke="rgba(196,181,253,.11)" strokeDasharray="3 6" vertical={false} /><XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#a49bbd', fontSize: 11 }} dy={9} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#a49bbd', fontSize: 11 }} /><Tooltip content={<ChartTooltip />} /><ReferenceLine y={80} stroke="#d5a766" strokeDasharray="5 5" /><Line type="monotone" dataKey="latency" name="Latency" stroke="#818cf8" strokeWidth={3} dot={false} activeDot={{ r: 5, fill: '#c4b5fd', stroke: '#100c1b', strokeWidth: 2 }} /></LineChart></ResponsiveContainer></div>
}

function TrafficChart() {
  return <div className="ops-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trafficData} margin={{ top: 14, right: 10, left: -19, bottom: 0 }}><defs><linearGradient id="trafficIn" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#6366f1" stopOpacity=".33" /><stop offset="100%" stopColor="#6366f1" stopOpacity=".015" /></linearGradient><linearGradient id="trafficOut" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#a78bfa" stopOpacity=".25" /><stop offset="100%" stopColor="#a78bfa" stopOpacity=".01" /></linearGradient></defs><CartesianGrid stroke="rgba(196,181,253,.11)" strokeDasharray="3 6" vertical={false} /><XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#a49bbd', fontSize: 11 }} dy={9} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#a49bbd', fontSize: 11 }} /><Tooltip content={<ChartTooltip />} /><Area type="monotone" dataKey="inbound" name="Inbound" stroke="#6366f1" strokeWidth={2.5} fill="url(#trafficIn)" /><Area type="monotone" dataKey="outbound" name="Outbound" stroke="#c4b5fd" strokeWidth={2.5} fill="url(#trafficOut)" /></AreaChart></ResponsiveContainer></div>
}

function HealthDonut() {
  return <div className="health-donut"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={deviceHealth} dataKey="value" nameKey="name" innerRadius="69%" outerRadius="92%" paddingAngle={3} stroke="none" startAngle={90} endAngle={-270}>{deviceHealth.map((item) => <Cell key={item.name} fill={item.color} />)}</Pie><Tooltip contentStyle={{ border: '1px solid rgba(117,155,195,.24)', borderRadius: 10, background: '#0c1522', color: '#eef6ff', fontSize: 12 }} /></PieChart></ResponsiveContainer><div className="health-donut__center"><b>248</b><span>DEVICES</span></div></div>
}

function Legend({ entries }) { return <div className="chart-legend">{entries.map(({ label, color }) => <span key={label}><i style={{ '--legend': color }} />{label}</span>)}</div> }

function statusForAgent(agent, run) {
  if (!run) return { label: 'Awaiting diagnosis', tone: 'idle' }
  if (run.status === 'loading') return { label: 'Workflow in progress', tone: 'running' }
  if (run.status === 'error') return { label: 'No result', tone: 'failed' }
  if (run.response?.agent_messages?.[agent.stage]) return { label: 'Completed', tone: 'complete' }
  if (agent.stage === 'fault_correlation' && run.response?.correlation_result) return { label: 'Completed', tone: 'complete' }
  if (agent.stage === 'recommendation_reporting' && run.response?.diagnostic_report) return { label: 'Completed', tone: 'complete' }
  if (run.response?.failures?.some((failure) => failure.stage === agent.stage)) return { label: 'Failed', tone: 'failed' }
  return { label: 'Not reached', tone: 'idle' }
}

function OverviewPage({ diagnosisRun, onNavigate }) {
  const apiReport = diagnosisRun?.response?.diagnostic_report
  return <>
    <PageHeader kicker="OPERATIONS / SNAPSHOT" title="See the shape of your network." description="A single view of the analysis workflow, with a clear line between illustrative data and actual diagnoses." action={<button className="primary-action" type="button" onClick={() => onNavigate('diagnosis')}><ScanSearch size={17} /> Start diagnosis <ArrowUpRight size={15} /></button>} />
    <SampleBanner>Overview charts and inventory are illustrative. This workspace does not poll network devices.</SampleBanner>
    {apiReport && <button className="latest-diagnosis-strip" type="button" onClick={() => onNavigate('diagnosis')}><span className="latest-diagnosis-strip__icon"><ShieldCheck size={18} /></span><span><small>LAST API DIAGNOSIS · {apiReport.diagnosis_id}</small><b>{apiReport.probable_root_cause || apiReport.incident_status.replaceAll('_', ' ')}</b></span><span className={`confidence-tag confidence-tag--${apiReport.confidence_category}`}>{apiReport.confidence_score == null ? apiReport.confidence_category : `${Math.round(apiReport.confidence_score * 100)}% · ${apiReport.confidence_category}`}</span><ArrowRight size={17} /></button>}
    <section className="kpi-grid" aria-label="Illustrative network KPIs"><KpiCard icon={ShieldCheck} label="Network health" value="98.6" unit="%" note="Sample snapshot" tone="green" trend="Stable" /><KpiCard icon={Server} label="Devices in sample" value="248" note="Illustrative inventory" tone="blue" trend="Sample" /><KpiCard icon={AlertTriangle} label="Incidents" value="03" note="Example records" tone="amber" trend="Demo" /><KpiCard icon={Activity} label="Mean latency" value="24.8" unit="ms" note="Sample 24h average" tone="cyan" trend="−3.2%" /></section>
    <div className="overview-main-grid"><Panel title="Latency over time" subtitle="Illustrative response-time profile · milliseconds" action={<span className="panel-data-tag"><i /> SAMPLE SERIES</span>} className="chart-surface chart-surface--large"><LatencyChart /><div className="chart-panel__foot"><Legend entries={[{ label: 'Latency', color: '#818cf8' }, { label: 'Prototype warning threshold', color: '#d5a766' }]} /><span>24 hour example</span></div></Panel><Panel title="Sample device health" subtitle="Example inventory distribution" action={<DemoFlag compact />} className="health-surface"><div className="health-surface__body"><HealthDonut /><div className="health-breakdown">{deviceHealth.map((item) => <div key={item.name}><span><i style={{ background: item.color }} />{item.name}</span><b>{item.value}</b></div>)}</div></div><small className="data-footnote">Illustrative distribution · not live-monitored</small></Panel></div>
    <div className="overview-secondary-grid"><Panel title="Agent workflow" subtitle="Role and last-run state" action={<button className="text-action" type="button" onClick={() => onNavigate('agents')}>Open roster <ArrowRight size={15} /></button>} className="agent-overview-surface"><div className="compact-agent-list">{agents.map((agent) => { const status = statusForAgent(agent, diagnosisRun); const Icon = agent.icon; return <div className="compact-agent-row agent-status-card--compact" key={agent.id}><span className={`compact-agent-row__icon compact-agent-row__icon--${agent.tone}`}><Icon size={16} /></span><span className="compact-agent-row__name"><b>{agent.name}</b><small>Agent {agent.id}</small></span><span className={`agent-state agent-state--${status.tone}`}><i />{status.label}</span></div> })}</div></Panel><Panel title="Recent activity" subtitle="Illustrative entries · sample timestamps" action={<button className="text-action" type="button" onClick={() => onNavigate('reports')}>View reports <ArrowRight size={15} /></button>} className="activity-surface"><ActivityList rows={activityRows.slice(0, 3)} /></Panel></div>
    <DashboardFootnote />
  </>
}

function AnalyticsPage() {
  return <>
    <PageHeader kicker="OPERATIONS / PERFORMANCE" title="Network analytics" description="Explore example performance patterns across latency, traffic and link utilization." action={<DemoFlag />} />
    <SampleBanner>Charts and KPI values below are sample visualizations, not telemetry returned by the backend.</SampleBanner>
    <section className="kpi-grid kpi-grid--three"><KpiCard icon={Activity} label="Average latency" value="24.8" unit="ms" note="Illustrative 24h average" tone="cyan" /><KpiCard icon={Zap} label="Packet loss" value="0.12" unit="%" note="Illustrative 24h average" tone="violet" /><KpiCard icon={Gauge} label="Link utilization" value="64" unit="%" note="Illustrative peak 78%" tone="blue" /></section>
    <div className="analytics-chart-grid"><Panel title="Latency profile" subtitle="Example average response time · milliseconds" action={<span className="chart-value">24.8 <small>ms avg</small></span>} className="chart-surface"><LatencyChart /><div className="chart-panel__foot"><Legend entries={[{ label: 'Latency', color: '#818cf8' }, { label: 'Prototype threshold', color: '#d5a766' }]} /><span>Sample interval · 4h</span></div></Panel><Panel title="Throughput profile" subtitle="Example traffic profile · Mbps" action={<span className="panel-data-tag">DEMO</span>} className="chart-surface"><TrafficChart /><div className="chart-panel__foot"><Legend entries={[{ label: 'Inbound', color: '#6366f1' }, { label: 'Outbound', color: '#c4b5fd' }]} /><span>Sample interval · 4h</span></div></Panel></div>
    <div className="insight-band"><span><ShieldCheck size={20} /></span><div><b>Analysis stays tied to submitted measurements</b><p>The Performance Agent evaluates request data with configurable prototype thresholds. These charts are separate illustrations and do not populate diagnosis findings.</p></div></div>
    <DashboardFootnote />
  </>
}

function ResourceBar({ value }) { const tone = value >= 80 ? 'high' : value >= 70 ? 'medium' : 'normal'; return <div className="resource-bar"><span><i><b className={`resource-bar__fill resource-bar__fill--${tone}`} style={{ width: `${value}%` }} /></i></span><strong>{value}%</strong></div> }

function InfrastructurePage() {
  return <>
    <PageHeader kicker="OPERATIONS / DEVICE CONDITION" title="Infrastructure health" description="A focused view of resource pressure, interface counters and device status." action={<DemoFlag />} />
    <SampleBanner>Device values and inventory below are illustrative. No devices are being polled.</SampleBanner>
    <section className="kpi-grid kpi-grid--four"><KpiCard icon={Cpu} label="Average CPU" value="48" unit="%" note="Example device set" tone="blue" /><KpiCard icon={HardDrive} label="Average memory" value="66" unit="%" note="Example device set" tone="cyan" /><KpiCard icon={Activity} label="Interface errors" value="18" note="Sample counters" tone="amber" /><KpiCard icon={ArrowDownRight} label="Queue drops" value="07" note="Sample counters" tone="violet" /></section>
    <Panel title="Device inventory" subtitle="Example resource snapshots · not live monitored" action={<span className="panel-data-tag"><i /> SAMPLE INVENTORY</span>} className="inventory-surface"><div className="table-scroll"><table className="inventory-table"><thead><tr><th>DEVICE</th><th>ROLE</th><th>CPU</th><th>MEMORY</th><th>IF ERRORS</th><th>QUEUE DROPS</th><th>STATUS</th></tr></thead><tbody>{infrastructureRows.map((device) => <tr key={device.device}><td><span className="device-cell"><i><Server size={15} /></i><b>{device.device}</b></span></td><td>{device.role}</td><td><ResourceBar value={device.cpu} /></td><td><ResourceBar value={device.memory} /></td><td><span className={device.errors ? 'counter counter--warn' : 'counter'}>{device.errors}</span></td><td><span className={device.drops ? 'counter counter--warn' : 'counter'}>{device.drops}</span></td><td><span className={`device-status device-status--${device.tone}`}><i />{device.status}</span></td></tr>)}</tbody></table></div></Panel>
    <div className="threshold-note"><span><AlertTriangle size={19} /></span><div><b>Prototype thresholds are configurable</b><p>Agent findings use the configured values supplied by the backend. This illustrative table is not an operational device inventory.</p></div></div>
    <DashboardFootnote />
  </>
}

function AgentsPage({ diagnosisRun, onNavigate }) {
  return <>
    <PageHeader kicker="INTELLIGENCE / SPECIALIST ROSTER" title="Five agents, coordinated." description="Each specialist owns one part of the workflow. Execution indicators reflect the most recent diagnosis request." action={<button className="primary-action" type="button" onClick={() => onNavigate('diagnosis')}><ScanSearch size={17} /> Run diagnosis</button>} />
    <div className="agent-pipeline"><div><span>01 — 03</span><b>Domain analysis</b><small>Performance · infrastructure · connectivity</small></div><ArrowRight size={18} /><div><span>04</span><b>Fault correlation</b><small>Rank evidence-supported causes</small></div><ArrowRight size={18} /><div><span>05</span><b>Unified report</b><small>Confidence · actions · limitations</small></div></div>
    <section className="agent-directory">{agents.map((agent) => { const Icon = agent.icon; const status = statusForAgent(agent, diagnosisRun); return <article className={`agent-card agent-card--${agent.tone}`} key={agent.id}><div className="agent-card__top"><span className={`agent-card__icon agent-card__icon--${agent.tone}`}><Icon size={20} /></span><span className={`agent-state agent-state--${status.tone}`}><i />{status.label}</span></div><div className="agent-card__number">AGENT {agent.id} <span>{agent.role}</span></div><h3>{agent.name}</h3><p>{agent.description}</p><div className="agent-card__focus">{agent.focus.map((item) => <span key={item}>{item}</span>)}</div></article> })}</section>
    <div className="agent-state-note"><span><Radio size={18} /></span><p>Agent states update only when a diagnosis request runs. The interface does not simulate background monitoring or agent execution.</p></div>
    <DashboardFootnote />
  </>
}

function messageEntries(diagnosisRun) {
  const response = diagnosisRun?.response
  if (!response) return demoMessages.map((entry) => ({ ...entry, illustrative: true }))
  const entries = []
  const labels = { performance: 'Performance Agent', infrastructure: 'Infrastructure Agent', connectivity: 'Connectivity Agent' }
  for (const key of ['performance', 'infrastructure', 'connectivity']) if (response.agent_messages?.[key]) entries.push({ key, label: labels[key], stage: 'DOMAIN ANALYSIS', message: response.agent_messages[key] })
  if (response.correlation_result) entries.push({ key: 'fault_correlation', label: 'Fault Correlation Agent', stage: 'CORRELATION', message: response.correlation_result })
  if (response.diagnostic_report) entries.push({ key: 'recommendation_reporting', label: 'Recommendation & Reporting Agent', stage: 'FINAL REPORT', message: response.diagnostic_report })
  return entries
}

function CommunicationPage({ diagnosisRun }) {
  const entries = messageEntries(diagnosisRun)
  const [selectedKey, setSelectedKey] = useState(entries[0]?.key || 'performance')
  const selected = entries.find((entry) => entry.key === selectedKey) || entries[0]
  const actual = Boolean(diagnosisRun?.response)
  return <>
    <PageHeader kicker="INTELLIGENCE / STRUCTURED MESSAGES" title="Inspect the evidence trail." description="Review the JSON messages that flow between agents. When a diagnosis has run, this view uses its actual response." action={actual ? <span className="actual-data-tag"><i /> API RESPONSE</span> : <DemoFlag />} />
    {!actual && <SampleBanner>Message bodies are illustrative schema examples and are not captured from an API run.</SampleBanner>}
    {actual && <div className="message-run-context"><span><Check size={17} /></span><div><small>ACTUAL DIAGNOSIS RESPONSE</small><b>{diagnosisRun.response.diagnosis_id}</b></div><strong>{diagnosisRun.response.status}</strong></div>}
    <div className="message-workspace"><aside className="message-index"><div className="message-index__heading"><div><span>WORKFLOW TRACE</span><b>{entries.length} messages</b></div><FileJson size={18} /></div>{entries.map((entry, index) => <button key={entry.key} type="button" className={`message-index__item${selected?.key === entry.key ? ' message-index__item--active' : ''}`} onClick={() => setSelectedKey(entry.key)}><span className="message-index__number">{String(index + 1).padStart(2, '0')}</span><span className="message-index__copy"><b>{entry.label}</b><small>{entry.stage}</small></span><ArrowRight size={15} /></button>)}<div className="message-index__foot"><ShieldCheck size={16} /> Shared diagnosis ID</div></aside>
      <section className="message-document"><header className="message-document__top"><div><span className="message-document__status"><i /> {actual ? 'CAPTURED RESPONSE' : 'SCHEMA EXAMPLE'}</span><h3>{selected?.label}</h3><p>{selected?.message?.diagnosis_id || 'No diagnosis ID'}</p></div><span className="message-format">JSON</span></header><pre><code>{JSON.stringify(selected?.message, null, 2)}</code></pre><footer><span><Check size={15} /> Evidence fields preserved</span><span>{actual ? 'FastAPI response' : 'Illustrative only'}</span></footer></section></div>
    <div className="message-principles"><div><span><Network size={17} /></span><b>One diagnosis ID</b><small>All stages share the same request identity.</small></div><div><span><GitBranch size={17} /></span><b>Traceable findings</b><small>Correlations point back to source-agent evidence.</small></div><div><span><ShieldCheck size={17} /></span><b>Uncertainty stays visible</b><small>Conflicts and limitations remain part of the output.</small></div></div>
    <DashboardFootnote />
  </>
}

function EvidenceList({ evidence }) {
  if (!evidence?.length) return <p className="empty-copy">No supporting evidence was reported.</p>
  return <div className="report-evidence-list">{evidence.map((item, index) => <article key={`${item.agent}-${item.finding_index}-${index}`}><span>{item.agent}.findings[{item.finding_index}]</span><b>{item.metric}: {String(item.value)}{item.device_id ? ` · ${item.device_id}` : ''}</b><small>{item.assessment}</small></article>)}</div>
}

function ActualReportCard({ report }) {
  const percent = report.confidence_score == null ? null : Math.round(report.confidence_score * 100)
  const heading = report.incident_status === 'no_fault_detected' ? 'No fault detected' : report.incident_status === 'insufficient_evidence' ? 'Insufficient evidence for a reliable cause' : report.probable_root_cause || 'No probable cause reported'
  return <section className="actual-report"><div className="actual-report__top"><div><span>ACTUAL API DIAGNOSIS · {report.diagnosis_id}</span><h3>{heading}</h3><p>{report.incident_status.replaceAll('_', ' ')} · {report.confidence_category} confidence</p></div><div className={`confidence-orb confidence-orb--${report.confidence_category}`} style={{ '--confidence': `${percent ?? 0}%` }}><b>{percent == null ? '—' : `${percent}%`}</b><span>CONFIDENCE</span></div></div>
    {report.probable_root_cause && <p className="actual-report__cause">{report.probable_root_cause}</p>}
    <div className="report-entity-grid">{[['Affected devices', report.affected_device_ids], ['Affected links', report.affected_link_ids], ['Affected segments', report.affected_segment_ids]].map(([label, values]) => <div key={label}><span>{label}</span><div>{values?.length ? values.map((value) => <code key={value}>{value}</code>) : <small>None reported</small>}</div></div>)}</div>
    <div className="report-detail-grid"><div><h4>Supporting evidence</h4><EvidenceList evidence={report.supporting_evidence} /></div><div><h4>Recommended actions</h4>{report.recommended_actions?.length ? <div className="report-action-list">{report.recommended_actions.map((item, index) => <article key={`${item.action}-${index}`}><span className={`priority-mark priority-mark--${item.priority}`}>{item.priority}</span><p>{item.action}</p></article>)}</div> : <p className="empty-copy">No corrective actions were reported.</p>}</div></div>
    {report.conflicts?.length > 0 && <div className="report-conflict"><b><AlertTriangle size={16} /> Conflicting evidence</b>{report.conflicts.map((item, index) => <p key={`${item.description}-${index}`}>{item.description}<small>{item.evidence.map((ref) => `${ref.agent}.findings[${ref.finding_index}]`).join(' · ')}</small></p>)}</div>}
    {(report.alternative_explanations?.length > 0 || report.uncertainties?.length > 0 || report.limitations?.length > 0) && <details className="report-uncertainty"><summary>Alternatives, uncertainty and limitations</summary>{report.alternative_explanations?.map((item, index) => <p key={`alt-${index}`}>{item}</p>)}{report.uncertainties?.map((item, index) => <p key={`unc-${index}`}>{item}</p>)}{report.limitations?.map((item, index) => <p key={`lim-${index}`}>{item}</p>)}</details>}
    <div className="report-sources"><b>Evidence sources</b><span>{report.evidence_sources?.length ? report.evidence_sources.join(' · ') : 'No source list reported'}</span></div>
  </section>
}

function ReportsPage({ diagnosisRun, onNavigate }) {
  const report = diagnosisRun?.response?.diagnostic_report
  return <>
    <PageHeader kicker="DIAGNOSE / REPORT REVIEW" title="Reports with the evidence attached." description="Inspect the latest report returned by the backend. This prototype does not store a report history service." action={report ? <span className="actual-data-tag"><i /> LATEST API REPORT</span> : null} />
    {report ? <ActualReportCard report={report} /> : <div className="report-empty"><span><FileText size={24} /></span><div><b>No API report in this session yet</b><p>Run a diagnosis to review its root cause, confidence, affected entities and evidence here.</p><button className="primary-action" type="button" onClick={() => onNavigate('diagnosis')}><ScanSearch size={16} /> Run a diagnosis</button></div></div>}
    <Panel title="Example activity" subtitle="Illustrative records · not backend history" action={<DemoFlag compact />} className="sample-activity"><ActivityList rows={activityRows} /></Panel>
    <DashboardFootnote />
  </>
}

function ActivityList({ rows }) {
  return <div className="activity-list">{rows.map((row) => <article className="activity-row" key={row.id}><span className={`activity-row__severity activity-row__severity--${row.tone}`}><i />{row.severity}</span><div className="activity-row__main"><b>{row.title}</b><small>{row.id} <i>·</i> {row.device}</small></div><div className="activity-row__cause"><span>{row.cause}</span><small>{row.time} · SAMPLE</small></div><ArrowUpRight size={16} /></article>)}</div>
}

function DashboardFootnote() { return <footer className="dashboard-footnote"><span><i /> SAMPLE DASHBOARD VALUES ARE ILLUSTRATIVE</span><span>NetCoop AI <b>·</b> Evidence-led network diagnosis</span></footer> }

function DiagnosisPage({ lastRun, onRunState }) {
  return <>
    <PageHeader kicker="DIAGNOSE / FASTAPI WORKFLOW" title="Build a diagnosis from observed data." description="Provide performance, infrastructure and connectivity telemetry. The same diagnosis ID follows each stage through the backend." action={<span className="endpoint-chip"><i /> POST /api/diagnose</span>} />
    <div className="diagnosis-context"><span><ShieldCheck size={18} /></span><p><b>Request input only</b> · fields begin blank. Add measured values and device identifiers; no sample telemetry is submitted automatically.</p></div>
    <div className="diagnosis-workspace"><div className="diagnosis-workspace__intro"><div><span>THREE INPUT SECTIONS</span><h3>Describe the incident</h3></div><div className="diagnosis-workspace__stages"><span>01 Performance</span><span>02 Infrastructure</span><span>03 Connectivity</span></div></div><DiagnosisForm onRunState={onRunState} /></div>
    <ApiRunResult run={lastRun} />
    <DashboardFootnote />
  </>
}

function ApiRunResult({ run }) {
  if (!run) return null
  const response = run.response
  const report = response?.diagnostic_report
  const correlation = response?.correlation_result
  if (run.status === 'loading') return <section aria-live="polite" className="api-result api-result--loading"><div className="api-result__heading"><span className="loading-orbit"><i /></span><div><span>ORCHESTRATED WORKFLOW</span><h3>Diagnosis in progress</h3><p>Domain analysis, fault correlation and report generation are running on the backend.</p></div></div><p>Diagnosis ID <code>{run.request.performance.diagnosis_id}</code></p><details className="api-json"><summary>Submitted request JSON</summary><pre>{JSON.stringify(run.request, null, 2)}</pre></details></section>
  if (run.status === 'error') return <section aria-live="polite" className="api-result api-result--error" role="alert"><div className="api-result__heading"><span className="api-result__icon"><AlertTriangle size={19} /></span><div><span>REQUEST NOT COMPLETED</span><h3>{run.error.kind === 'validation' ? 'Request rejected' : run.error.kind === 'connection' ? 'Backend connection failed' : 'Diagnosis request failed'}</h3><p>{run.error.summary}</p></div></div>{run.error.status && <p className="api-http-status">HTTP {run.error.status}</p>}{run.error.details?.length > 0 && <ul className="api-error-list">{run.error.details.map((detail) => <li key={detail}>{detail}</li>)}</ul>}{run.error.body && <details className="api-json"><summary>Backend error response</summary><pre>{JSON.stringify(run.error.body, null, 2)}</pre></details>}<details className="api-json"><summary>Submitted request JSON</summary><pre>{JSON.stringify(run.request, null, 2)}</pre></details></section>
  if (!response) return null
  const partial = response.status === 'partial'
  return <section aria-live="polite" className={`api-result${partial ? ' api-result--partial' : ' api-result--complete'}`}><div className="api-result__heading"><span className="api-result__icon">{partial ? <AlertTriangle size={19} /> : <Check size={19} />}</span><div><span>{partial ? 'PARTIAL WORKFLOW' : 'WORKFLOW COMPLETE'}</span><h3>{partial ? 'Partial diagnosis returned' : 'Diagnostic report returned'}</h3><p>{response.diagnosis_id} · {run.completedAt ? new Date(run.completedAt).toLocaleTimeString() : 'just now'}</p></div><strong>{partial ? 'PARTIAL' : 'COMPLETE'}</strong></div>
    {response.failures?.length > 0 && <div className="api-failures"><b>Stages that did not complete</b>{response.failures.map((failure, index) => <p key={`${failure.stage}-${index}`}><strong>{failure.stage}</strong> · {failure.error_type}: {failure.message}</p>)}</div>}
    {report && <ActualReportCard report={report} />}
    {correlation && <details className="api-correlation"><summary>Fault correlation · {correlation.status.replaceAll('_', ' ')} · {correlation.hypotheses.length} hypotheses</summary><p>{correlation.summary}</p>{correlation.conflicts?.map((conflict, index) => <div className="report-conflict" key={`${conflict.description}-${index}`}><b><AlertTriangle size={15} /> Conflict</b><p>{conflict.description}</p><small>{conflict.evidence.map((item) => `${item.agent}.findings[${item.finding_index}]`).join(' · ')}</small></div>)}{correlation.hypotheses.map((item) => <article className="correlation-hypothesis" key={`${item.rank}-${item.cause}`}><div><b>#{item.rank} {item.cause}</b><span>{Math.round(item.confidence * 100)}% heuristic confidence</span></div><p>{item.explanation}</p><small>{item.evidence.length} evidence references</small></article>)}</details>}
    <div className="api-agent-messages"><div className="api-agent-messages__heading"><b>Domain agent messages</b><span>{Object.keys(response.agent_messages || {}).length} / 3</span></div>{Object.entries(response.agent_messages || {}).map(([key, message]) => <details className="api-agent-message" key={key}><summary><span><i />{key}</span><small>{message.samples_analyzed} samples · {message.findings.length} findings</small><ChevronDown size={15} /></summary><p>{message.summary}</p><div>{message.findings.map((finding, index) => <article key={`${finding.metric}-${index}`}><span className={`finding-level finding-level--${finding.severity}`}>{finding.severity}</span><b>{finding.metric}</b><strong>{String(finding.value)} {finding.unit}</strong><small>{finding.assessment}</small></article>)}</div></details>)}</div>
    <details className="api-json"><summary>Submitted request JSON</summary><pre>{JSON.stringify(run.request, null, 2)}</pre></details><details className="api-json"><summary>Full API response JSON</summary><pre>{JSON.stringify(response, null, 2)}</pre></details>
  </section>
}

function apiStatus(run, apiReachable) {
  if (!run) return apiReachable === null
    ? { label: 'Checking backend', tone: 'idle' }
    : apiReachable
      ? { label: 'Backend available', tone: 'complete' }
      : { label: 'Backend unavailable', tone: 'failed' }
  if (run.status === 'loading') return { label: 'Request in progress', tone: 'running' }
  if (run.status === 'error') return { label: run.error.kind === 'connection' ? 'Backend unavailable' : run.error.kind === 'validation' ? 'Request rejected' : 'Request failed', tone: 'failed' }
  return run.status === 'partial' ? { label: 'Partial response', tone: 'warning' } : { label: 'Response received', tone: 'complete' }
}

function Dashboard() {
  const { diagnosisRun, setDiagnosisRun } = useContext(DiagnosisRunContext)
  const [location, setLocation] = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [now, setNow] = useState(() => new Date())
  const [apiReachable, setApiReachable] = useState(null)
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 1000); return () => window.clearInterval(timer) }, [])
  useEffect(() => {
    const controller = new AbortController()
    fetch('/health', { signal: controller.signal })
      .then((response) => setApiReachable(response.ok))
      .catch((error) => { if (error.name !== 'AbortError') setApiReachable(false) })
    return () => controller.abort()
  }, [])
  const activePage = Object.entries(pagePaths).find(([, path]) => path === location)?.[0] || 'overview'
  const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const status = apiStatus(diagnosisRun, apiReachable)
  const navigate = (page) => setLocation(pagePaths[page] || pagePaths.overview)
  const renderPage = () => {
    switch (activePage) {
      case 'analytics': return <AnalyticsPage />
      case 'infrastructure': return <InfrastructurePage />
      case 'agents': return <AgentsPage diagnosisRun={diagnosisRun} onNavigate={navigate} />
      case 'communication': return <CommunicationPage diagnosisRun={diagnosisRun} />
      case 'diagnosis': return <DiagnosisPage lastRun={diagnosisRun} onRunState={setDiagnosisRun} />
      case 'reports': return <ReportsPage diagnosisRun={diagnosisRun} onNavigate={navigate} />
      default: return <OverviewPage diagnosisRun={diagnosisRun} onNavigate={navigate} />
    }
  }
  return <div className="operations-app"><Sidebar activePage={activePage} onNavigate={navigate} open={menuOpen} onClose={() => setMenuOpen(false)} apiStatus={status} /><div className="operations-main"><Topbar title={titles[activePage]} time={time} apiStatus={status} onMenu={() => setMenuOpen(true)} onDiagnosis={() => navigate('diagnosis')} /><main className="operations-content">{renderPage()}</main></div></div>
}

export default Dashboard

