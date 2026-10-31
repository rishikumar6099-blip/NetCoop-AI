import { useState } from 'react'
import {
  Activity,
  Cpu,
  GitBranch,
  Plus,
  RefreshCw,
  Server,
  ShieldCheck,
  Trash2,
  Wifi,
} from 'lucide-react'
import { buildDiagnosisRequest, describeApiError, submitDiagnosis } from '../services/diagnosisApi.js'
import { SCENARIO_PRESETS } from '../data/scenarioPresets.js'

const performanceFields = [
  { name: 'latency_ms', label: 'Latency', suffix: 'ms', min: 0, step: 'any' },
  { name: 'jitter_ms', label: 'Jitter', suffix: 'ms', min: 0, step: 'any' },
  { name: 'packet_loss_pct', label: 'Packet loss', suffix: '%', min: 0, max: 100, step: 'any' },
  { name: 'throughput_mbps', label: 'Throughput', suffix: 'Mbps', min: 0, step: 'any' },
  { name: 'link_utilization_pct', label: 'Link utilisation', suffix: '%', min: 0, max: 100, step: 'any' },
]

const infrastructureFields = [
  { name: 'cpu_utilization_pct', label: 'CPU utilisation', suffix: '%', min: 0, max: 100, step: 'any' },
  { name: 'memory_utilization_pct', label: 'Memory utilisation', suffix: '%', min: 0, max: 100, step: 'any' },
  { name: 'interface_errors', label: 'Interface errors', suffix: 'count', min: 0, step: 1, integer: true },
  { name: 'egress_queue_drops', label: 'Egress queue drops', suffix: 'count', min: 0, step: 1, integer: true },
]

function createDiagnosisId() {
  const token = globalThis.crypto?.randomUUID?.() || `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
  return `diag-${token}`
}

function blankPerformanceSample() {
  return { device_id: '', interface_id: '', latency_ms: '', jitter_ms: '', packet_loss_pct: '', throughput_mbps: '', link_utilization_pct: '' }
}

function blankInfrastructureSample() {
  return { device_id: '', interface_id: '', cpu_utilization_pct: '', memory_utilization_pct: '', interface_errors: '', egress_queue_drops: '', device_status: '' }
}

function blankDevice() {
  return { device_id: '', segment_id: '', reachability: '' }
}

function blankLink() {
  return { link_id: '', source_device_id: '', target_device_id: '', status: 'unknown' }
}

function Field({ label, value, onChange, type = 'text', placeholder = '', suffix, min, max, step, required = false, invalid = false, id, autoComplete }) {
  return (
    <label className={`diagnosis-field${invalid ? ' diagnosis-field--invalid' : ''}`} htmlFor={id}>
      <span className="diagnosis-field__label">{label}{required && <i>Required</i>}</span>
      <span className="diagnosis-field__control">
        <input
          autoComplete={autoComplete || 'off'}
          id={id}
          max={max}
          min={min}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          required={required}
          step={step}
          type={type}
          value={value}
        />
        {suffix && <small>{suffix}</small>}
      </span>
    </label>
  )
}

function SelectField({ label, value, onChange, options, id, placeholder = 'Select status' }) {
  return (
    <label className="diagnosis-field" htmlFor={id}>
      <span className="diagnosis-field__label">{label}</span>
      <span className="diagnosis-field__control diagnosis-field__control--select">
        <select id={id} onChange={(event) => onChange(event.target.value)} value={value}>
          <option value="">{placeholder}</option>
          {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </span>
    </label>
  )
}

function SectionHeading({ icon: Icon, number, title, description, action }) {
  return (
    <div className="diagnosis-form__section-heading">
      <span className="diagnosis-form__section-icon"><Icon size={17} /></span>
      <div className="diagnosis-form__section-copy"><span>INPUT {number}</span><h3>{title}</h3><p>{description}</p></div>
      {action}
    </div>
  )
}

function AddButton({ children, onClick }) {
  return <button className="diagnosis-add-button" onClick={onClick} type="button"><Plus size={14} />{children}</button>
}

function RemoveButton({ onClick, label }) {
  return <button aria-label={label} className="diagnosis-remove-button" onClick={onClick} title="Remove row" type="button"><Trash2 size={14} /></button>
}

function SampleFields({ sample, index, kind, update, remove, canRemove, errors }) {
  const isPerformance = kind === 'performance'
  const fields = isPerformance ? performanceFields : infrastructureFields
  const prefix = `${kind}-${index}`
  return (
    <div className="diagnosis-sample-card">
      <div className="diagnosis-sample-card__header">
        <span><i>{String(index + 1).padStart(2, '0')}</i>{isPerformance ? 'Performance sample' : 'Infrastructure sample'}</span>
        {canRemove && <RemoveButton label={`Remove ${isPerformance ? 'performance' : 'infrastructure'} sample ${index + 1}`} onClick={remove} />}
      </div>
      <div className={`diagnosis-fields-grid diagnosis-fields-grid--identity${isPerformance ? '' : ' diagnosis-fields-grid--identity-infra'}`}>
        <Field id={`${prefix}-device`} label="Device ID" onChange={(value) => update('device_id', value)} placeholder="e.g. RTR-EDGE-01" required value={sample.device_id} invalid={errors.some((error) => error.includes(`${isPerformance ? 'Performance' : 'Infrastructure'} sample ${index + 1}`) && error.includes('device ID'))} />
        <Field id={`${prefix}-interface`} label="Interface ID" onChange={(value) => update('interface_id', value)} placeholder="e.g. xe-0/0/1" value={sample.interface_id} />
        {!isPerformance && <SelectField id={`${prefix}-status`} label="Device status" onChange={(value) => update('device_status', value)} options={[{ value: 'online', label: 'Online' }, { value: 'offline', label: 'Offline' }, { value: 'degraded', label: 'Degraded' }]} placeholder="Not provided" value={sample.device_status} />}
      </div>
      <div className={`diagnosis-fields-grid ${isPerformance ? 'diagnosis-fields-grid--metrics' : 'diagnosis-fields-grid--infra'}`}>
        {fields.map((field) => (
          <Field
            id={`${prefix}-${field.name}`}
            key={field.name}
            label={field.label}
            max={field.max}
            min={field.min}
            onChange={(value) => update(field.name, value)}
            step={field.step}
            suffix={field.suffix}
            type="number"
            value={sample[field.name]}
          />
        ))}
      </div>
    </div>
  )
}

function validateNumericFields(samples, fields, sectionName) {
  const errors = []
  samples.forEach((sample, index) => {
    for (const field of fields) {
      const raw = sample[field.name]
      if (raw === '') continue
      const value = Number(raw)
      const fieldName = `${sectionName} sample ${index + 1} · ${field.label}`
      if (!Number.isFinite(value)) errors.push(`${fieldName}: enter a valid number.`)
      else if (field.min !== undefined && value < field.min) errors.push(`${fieldName}: must be at least ${field.min}.`)
      else if (field.max !== undefined && value > field.max) errors.push(`${fieldName}: must be no more than ${field.max}.`)
      else if (field.integer && !Number.isInteger(value)) errors.push(`${fieldName}: enter a whole number.`)
    }
  })
  return errors
}

function validateForm({ diagnosisId, performanceSamples, infrastructureSamples, devices, links }) {
  const errors = []
  if (!diagnosisId.trim()) errors.push('Diagnosis ID is required.')
  if (!performanceSamples.length) errors.push('Add at least one performance sample.')
  if (!infrastructureSamples.length) errors.push('Add at least one infrastructure sample.')

  for (const [sectionName, samples, fields] of [
    ['Performance', performanceSamples, performanceFields],
    ['Infrastructure', infrastructureSamples, infrastructureFields],
  ]) {
    samples.forEach((sample, index) => {
      if (!sample.device_id.trim()) errors.push(`${sectionName} sample ${index + 1}: device ID is required.`)
      if (!fields.some((field) => sample[field.name] !== '') && !(sectionName === 'Infrastructure' && sample.device_status)) {
        errors.push(`${sectionName} sample ${index + 1}: enter at least one measurement.`)
      }
    })
    errors.push(...validateNumericFields(samples, fields, sectionName))
  }

  if (!devices.length && !links.length) errors.push('Connectivity needs at least one device or link.')
  devices.forEach((device, index) => {
    if (!device.device_id.trim()) errors.push(`Connectivity device ${index + 1}: device ID is required.`)
  })
  links.forEach((link, index) => {
    if (!link.link_id.trim()) errors.push(`Link ${index + 1}: link ID is required.`)
    if (!link.source_device_id.trim()) errors.push(`Link ${index + 1}: source device ID is required.`)
    if (!link.target_device_id.trim()) errors.push(`Link ${index + 1}: target device ID is required.`)
  })

  const deviceIds = devices.map((device) => device.device_id.trim()).filter(Boolean)
  if (new Set(deviceIds).size !== deviceIds.length) errors.push('Connectivity device IDs must be unique.')
  const linkIds = links.map((link) => link.link_id.trim()).filter(Boolean)
  if (new Set(linkIds).size !== linkIds.length) errors.push('Link IDs must be unique.')

  return [...new Set(errors)]
}

function makeErrorSummary(error) {
  switch (error.kind) {
    case 'validation': return 'The backend rejected this request. Correct the fields listed below and submit again.'
    case 'connection': return 'The backend could not be reached. Your request was not replaced with demo data.'
    case 'http': return `The backend returned an HTTP ${error.status || 'error'} response.`
    default: return 'The backend returned an unexpected response. No diagnosis result is available.'
  }
}

function DiagnosisForm({ onRunState }) {
  const [diagnosisId, setDiagnosisId] = useState(createDiagnosisId)
  const [performanceSamples, setPerformanceSamples] = useState([blankPerformanceSample()])
  const [infrastructureSamples, setInfrastructureSamples] = useState([blankInfrastructureSample()])
  const [devices, setDevices] = useState([blankDevice()])
  const [links, setLinks] = useState([])
  const [errors, setErrors] = useState([])
  const [submitting, setSubmitting] = useState(false)

  const updateRow = (setter, index, key, value) => {
    setter((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row))
    setErrors([])
  }
  const removeRow = (setter, index) => {
    setter((rows) => rows.filter((_, rowIndex) => rowIndex !== index))
    setErrors([])
  }
  const addRow = (setter, createRow) => {
    setter((rows) => [...rows, createRow()])
    setErrors([])
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const input = { diagnosisId, performanceSamples, infrastructureSamples, devices, links }
    const validationErrors = validateForm(input)
    setErrors(validationErrors)
    if (validationErrors.length) {
      document.getElementById('diagnosis-form-errors')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }

    const request = buildDiagnosisRequest(input)
    const startedAt = new Date().toISOString()
    setSubmitting(true)
    onRunState({ request, response: null, error: null, status: 'loading', startedAt, completedAt: null })
    try {
      const response = await submitDiagnosis(request)
      onRunState({
        request,
        response,
        error: null,
        status: response.status,
        startedAt,
        completedAt: new Date().toISOString(),
      })
    } catch (error) {
      const details = describeApiError(error)
      onRunState({
        request,
        response: null,
        error: { ...details, summary: makeErrorSummary(details) },
        status: 'error',
        startedAt,
        completedAt: new Date().toISOString(),
      })
    } finally {
      setSubmitting(false)
    }
  }

  function loadScenarioPreset(preset) {
    setDiagnosisId(`diag-${preset.id}-${Date.now().toString(36).slice(-4)}`)
    setPerformanceSamples(
      preset.data.performanceSamples.map((s) => ({ ...blankPerformanceSample(), ...s }))
    )
    setInfrastructureSamples(
      preset.data.infrastructureSamples.map((s) => ({ ...blankInfrastructureSample(), ...s }))
    )
    setDevices(preset.data.devices.map((d) => ({ ...blankDevice(), ...d })))
    setLinks(preset.data.links.map((l) => ({ ...blankLink(), ...l })))
    setErrors([])
  }

  return (
    <form className="diagnosis-request-form" noValidate onSubmit={handleSubmit}>
      <div className="diagnosis-preset-panel" style={{ background: 'rgba(30, 27, 75, 0.45)', border: '1px solid rgba(139, 92, 246, 0.25)', borderRadius: '10px', padding: '12px 16px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <b style={{ color: '#c4b5fd', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={14} color="#818cf8" /> Core Hackathon Scenarios (1-Click Presets)
            </b>
            <p style={{ margin: '2px 0 0 0', fontSize: '11px', color: '#94a3b8' }}>Load pre-calibrated scenario telemetry to test multi-agent diagnosis instantly.</p>
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {SCENARIO_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className="button"
                style={{ fontSize: '11px', padding: '4px 10px', height: 'auto', background: 'rgba(99, 102, 241, 0.2)', borderColor: 'rgba(99, 102, 241, 0.4)', color: '#e2e8f0', borderRadius: '6px', cursor: 'pointer' }}
                onClick={() => loadScenarioPreset(preset)}
                title={preset.description}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="diagnosis-id-panel">
        <div><span className="diagnosis-id-panel__icon"><GitBranch size={17} /></span><span><b>Diagnosis ID</b><small>Shared across all three telemetry sections</small></span></div>
        <code>{diagnosisId}</code>
        <button aria-label="Generate a new diagnosis ID" className="diagnosis-id-panel__refresh" disabled={submitting} onClick={() => setDiagnosisId(createDiagnosisId())} title="Generate new ID" type="button"><RefreshCw size={14} /></button>
      </div>

      <section className="diagnosis-form-section">
        <SectionHeading icon={Activity} number="01" title="Performance telemetry" description="Each sample needs a device ID and at least one measurement." action={<AddButton onClick={() => addRow(setPerformanceSamples, blankPerformanceSample)}>Add sample</AddButton>} />
        <div className="diagnosis-sample-list">{performanceSamples.map((sample, index) => <SampleFields canRemove={performanceSamples.length > 1} errors={errors} index={index} key={`performance-${index}`} kind="performance" remove={() => removeRow(setPerformanceSamples, index)} sample={sample} update={(key, value) => updateRow(setPerformanceSamples, index, key, value)} />)}</div>
      </section>

      <section className="diagnosis-form-section">
        <SectionHeading icon={Cpu} number="02" title="Infrastructure telemetry" description="Add device health measurements. CPU and memory accept 0–100%; counters must be whole numbers." action={<AddButton onClick={() => addRow(setInfrastructureSamples, blankInfrastructureSample)}>Add sample</AddButton>} />
        <div className="diagnosis-sample-list">{infrastructureSamples.map((sample, index) => <SampleFields canRemove={infrastructureSamples.length > 1} errors={errors} index={index} key={`infrastructure-${index}`} kind="infrastructure" remove={() => removeRow(setInfrastructureSamples, index)} sample={sample} update={(key, value) => updateRow(setInfrastructureSamples, index, key, value)} />)}</div>
      </section>

      <section className="diagnosis-form-section">
        <SectionHeading icon={Wifi} number="03" title="Connectivity topology" description="Provide known devices and links. Segment and reachability details may be left blank if unknown." action={<AddButton onClick={() => addRow(setDevices, blankDevice)}>Add device</AddButton>} />
        <div className="topology-list">
          {devices.map((device, index) => (
            <div className="topology-row" key={`device-${index}`}>
              <div className="topology-row__label"><span><Server size={14} /></span><b>DEVICE {String(index + 1).padStart(2, '0')}</b></div>
              <Field id={`topology-device-${index}`} label="Device ID" onChange={(value) => updateRow(setDevices, index, 'device_id', value)} placeholder="e.g. RTR-EDGE-01" required value={device.device_id} />
              <Field id={`topology-segment-${index}`} label="Segment ID" onChange={(value) => updateRow(setDevices, index, 'segment_id', value)} placeholder="e.g. branch-west" value={device.segment_id} />
              <SelectField id={`topology-reachability-${index}`} label="Reachability" onChange={(value) => updateRow(setDevices, index, 'reachability', value)} options={[{ value: 'reachable', label: 'Reachable' }, { value: 'unreachable', label: 'Unreachable' }, { value: 'unknown', label: 'Unknown' }]} placeholder="Not provided" value={device.reachability} />
              <RemoveButton label={`Remove device ${index + 1}`} onClick={() => removeRow(setDevices, index)} />
            </div>
          ))}
          {!devices.length && <p className="topology-empty">No devices added. Add a device or a link to provide connectivity input.</p>}
        </div>
        <div className="topology-links-heading"><div><span><GitBranch size={15} /></span><div><b>Network links</b><small>Link endpoints must have IDs; unknown status is allowed.</small></div></div><AddButton onClick={() => addRow(setLinks, blankLink)}>Add link</AddButton></div>
        <div className="topology-list topology-list--links">
          {links.map((link, index) => (
            <div className="topology-row topology-row--link" key={`link-${index}`}>
              <div className="topology-row__label"><span><GitBranch size={14} /></span><b>LINK {String(index + 1).padStart(2, '0')}</b></div>
              <Field id={`topology-link-id-${index}`} label="Link ID" onChange={(value) => updateRow(setLinks, index, 'link_id', value)} placeholder="e.g. L-EDGE-01" required value={link.link_id} />
              <Field id={`topology-link-source-${index}`} label="Source device ID" onChange={(value) => updateRow(setLinks, index, 'source_device_id', value)} placeholder="Source device" required value={link.source_device_id} />
              <Field id={`topology-link-target-${index}`} label="Target device ID" onChange={(value) => updateRow(setLinks, index, 'target_device_id', value)} placeholder="Target device" required value={link.target_device_id} />
              <SelectField id={`topology-link-status-${index}`} label="Link status" onChange={(value) => updateRow(setLinks, index, 'status', value)} options={[{ value: 'up', label: 'Up' }, { value: 'down', label: 'Down' }, { value: 'unknown', label: 'Unknown' }]} value={link.status} />
              <RemoveButton label={`Remove link ${index + 1}`} onClick={() => removeRow(setLinks, index)} />
            </div>
          ))}
          {!links.length && <p className="topology-empty">No links added. Links are optional when device observations are supplied.</p>}
        </div>
      </section>

      {errors.length > 0 && <div aria-live="polite" className="diagnosis-validation-errors" id="diagnosis-form-errors" role="alert"><b>Check the request fields</b><ul>{errors.map((error) => <li key={error}>{error}</li>)}</ul></div>}

      <div className="diagnosis-form-submit">
        <p><ShieldCheck size={15} /> The backend validates this request before analysis. No automatic remediation is performed.</p>
        <button className="button button--primary diagnosis-submit-button" disabled={submitting} type="submit">
          {submitting ? <><span className="diagnosis-spinner" /> Running five-agent diagnosis…</> : <>Run network diagnosis <GitBranch size={15} /> </>}
        </button>
      </div>
    </form>
  )
}

export default DiagnosisForm
