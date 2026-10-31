import { useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  Check,
  Cpu,
  FileCode,
  FileJson,
  Layers,
  Network,
  Radio,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Zap,
} from 'lucide-react'
import { validateInteroperability } from '../services/diagnosisApi.js'

const SAMPLES = {
  diagnosis: {
    label: 'Full Diagnosis (Alien Aliases & Units)',
    payload: {
      schema_version: '1.0',
      performance: {
        diagnosis_id: 'sample-interop-diag-01',
        samples: [
          {
            device_id: 'RTR-CORE-01',
            rtt: '45ms',
            loss_pct: '2.5%',
            throughput_mbps: '850Mbps',
          },
        ],
      },
      infrastructure: {
        diagnosis_id: 'sample-interop-diag-01',
        samples: [
          {
            device_id: 'RTR-CORE-01',
            cpu_pct: '64%',
            crc_errors: 12,
            flaps: 3,
            device_status: 'online',
          },
        ],
      },
      connectivity: {
        diagnosis_id: 'sample-interop-diag-01',
        nodes: [
          { id: 'RTR-CORE-01', state: 'ONLINE', vlan: 'vlan-100' },
          { id: 'SW-DIST-01', state: 'UP', vlan: 'vlan-100' },
        ],
        edges: [
          {
            id: 'L-CORE-DIST',
            from: 'RTR-CORE-01',
            to: 'SW-DIST-01',
            state: 'ACTIVE',
            type: 'copper',
          },
        ],
      },
    },
  },
  performance: {
    label: 'Performance Telemetry (String Units & Aliases)',
    payload: {
      schema_version: '1.0',
      diagnosis_id: 'sample-perf-01',
      samples: [
        {
          device_id: 'AP-WEST-02',
          ping_ms: '120ms',
          loss: '0.04',
          rssi: '-82dBm',
        },
      ],
    },
  },
  infrastructure: {
    label: 'Infrastructure Telemetry (Resource & Error Aliases)',
    payload: {
      schema_version: '1.0',
      diagnosis_id: 'sample-infra-01',
      samples: [
        {
          device_id: 'SW-AGG-04',
          cpu_usage: '78%',
          mem_pct: '84%',
          rx_errors: 45,
          queue_drops: 8,
          status: 'online',
        },
      ],
    },
  },
  incompatible: {
    label: 'Incompatible Telemetry (Unsupported Units & Schema)',
    payload: {
      schema_version: '2.0',
      performance: {
        diagnosis_id: 'sample-bad-01',
        samples: [
          {
            device_id: 'ROUTER-X',
            latency: '50Mbps',
            packet_loss: '150%',
          },
        ],
      },
    },
  },
}

export default function InteropValidator() {
  const [domain, setDomain] = useState('diagnosis')
  const [schemaVersion, setSchemaVersion] = useState('1.0')
  const [jsonText, setJsonText] = useState(() =>
    JSON.stringify(SAMPLES.diagnosis.payload, null, 2)
  )
  const [validating, setValidating] = useState(false)
  const [parseError, setParseError] = useState(null)
  const [validationResult, setValidationResult] = useState(null)

  const handleLoadSample = (sampleKey) => {
    const s = SAMPLES[sampleKey]
    if (!s) return
    if (sampleKey === 'incompatible') {
      setDomain('diagnosis')
      setSchemaVersion('2.0')
    } else {
      setDomain(sampleKey)
      setSchemaVersion('1.0')
    }
    setJsonText(JSON.stringify(s.payload, null, 2))
    setParseError(null)
    setValidationResult(null)
  }

  const handleValidate = async () => {
    setParseError(null)
    let parsed
    try {
      parsed = JSON.parse(jsonText)
    } catch (err) {
      setParseError(`JSON Syntax Error: ${err.message}`)
      return
    }

    setValidating(true)
    try {
      const res = await validateInteroperability({
        domain,
        payload: parsed,
        schema_version: schemaVersion.trim() || undefined,
      })
      setValidationResult(res)
    } catch (err) {
      setValidationResult({
        status: 'incompatible',
        schema_version: schemaVersion,
        domain,
        errors: [{ error_type: 'ConnectionError', message: err.message }],
        recognized_aliases: [],
        field_mappings: [],
        unit_conversions: [],
        missing_required_fields: [],
        normalized_payload: null,
      })
    } finally {
      setValidating(false)
    }
  }

  return (
    <div className="interop-validator-page">
      <div className="page-heading">
        <div>
          <div className="page-heading__kicker">INTELLIGENCE / ADVANCED INTEROPERABILITY</div>
          <h2>Telemetry Interoperability Validator</h2>
          <p>
            Test heterogeneous network telemetry against Phase 3 schema compatibility rules,
            field alias resolvers, unit scale converters, and evidence traceability verifiers.
          </p>
        </div>
        <div className="page-heading__action">
          <span className="endpoint-chip">
            <i /> POST /api/interop/validate
          </span>
        </div>
      </div>

      {/* Preset loaders banner */}
      <div
        className="interop-preset-panel"
        style={{
          background: 'rgba(30, 27, 75, 0.45)',
          border: '1px solid rgba(139, 92, 246, 0.25)',
          borderRadius: '10px',
          padding: '12px 16px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <b style={{ color: '#c4b5fd', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <FileCode size={15} color="#818cf8" /> Load Test Payloads with Aliases & String Units
            </b>
            <p style={{ margin: '3px 0 0 0', fontSize: '11px', color: '#94a3b8' }}>
              Select a sample to populate the raw JSON payload below:
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="button button--secondary"
              style={{ fontSize: '11px', padding: '4px 10px', height: 'auto', background: 'rgba(99, 102, 241, 0.2)', borderColor: 'rgba(99, 102, 241, 0.4)', color: '#e2e8f0', borderRadius: '6px', cursor: 'pointer' }}
              onClick={() => handleLoadSample('diagnosis')}
            >
              Multi-Agent Aliases
            </button>
            <button
              type="button"
              className="button button--secondary"
              style={{ fontSize: '11px', padding: '4px 10px', height: 'auto', background: 'rgba(99, 102, 241, 0.2)', borderColor: 'rgba(99, 102, 241, 0.4)', color: '#e2e8f0', borderRadius: '6px', cursor: 'pointer' }}
              onClick={() => handleLoadSample('performance')}
            >
              Performance Only
            </button>
            <button
              type="button"
              className="button button--secondary"
              style={{ fontSize: '11px', padding: '4px 10px', height: 'auto', background: 'rgba(99, 102, 241, 0.2)', borderColor: 'rgba(99, 102, 241, 0.4)', color: '#e2e8f0', borderRadius: '6px', cursor: 'pointer' }}
              onClick={() => handleLoadSample('infrastructure')}
            >
              Infrastructure Only
            </button>
            <button
              type="button"
              className="button button--secondary"
              style={{ fontSize: '11px', padding: '4px 10px', height: 'auto', background: 'rgba(239, 68, 68, 0.15)', borderColor: 'rgba(239, 68, 68, 0.35)', color: '#fca5a5', borderRadius: '6px', cursor: 'pointer' }}
              onClick={() => handleLoadSample('incompatible')}
            >
              Incompatible / Rejection Test
            </button>
          </div>
        </div>
      </div>

      {/* Editor & Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: '20px', marginBottom: '24px' }}>
        {/* Left Column: Input Payload */}
        <section
          className="surface-panel"
          style={{
            background: 'var(--ops-surface)',
            border: '1px solid var(--ops-stroke)',
            borderRadius: '12px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '14px', margin: 0, color: '#f1edfc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileJson size={16} color="#818cf8" /> Raw Telemetry Input Payload
            </h3>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <label style={{ fontSize: '12px', color: '#a49bbd' }}>Domain:</label>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                style={{
                  background: '#151020',
                  color: '#f1edfc',
                  border: '1px solid rgba(152, 134, 203, 0.3)',
                  borderRadius: '6px',
                  padding: '3px 8px',
                  fontSize: '12px',
                }}
              >
                <option value="diagnosis">diagnosis (Multi-Agent)</option>
                <option value="performance">performance</option>
                <option value="infrastructure">infrastructure</option>
                <option value="connectivity">connectivity</option>
              </select>
            </div>
          </div>

          <textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            rows={18}
            spellCheck="false"
            style={{
              width: '100%',
              background: '#090811',
              color: '#c4b5fd',
              fontFamily: "'Fira Code', monospace",
              fontSize: '12px',
              lineHeight: '1.5',
              padding: '12px',
              border: '1px solid rgba(152, 134, 203, 0.2)',
              borderRadius: '8px',
              resize: 'vertical',
            }}
          />

          {parseError && (
            <div style={{ marginTop: '8px', padding: '8px 12px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', color: '#fca5a5', fontSize: '12px' }}>
              <AlertTriangle size={14} style={{ display: 'inline', marginRight: '6px' }} />
              {parseError}
            </div>
          )}

          <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: '#7f759b' }}>
              Validates schema, detects aliases, and verifies units without running agents.
            </span>
            <button
              type="button"
              className="button button--primary"
              disabled={validating}
              onClick={handleValidate}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                border: 'none',
                borderRadius: '6px',
                color: '#fff',
                fontWeight: 600,
                fontSize: '12px',
                cursor: validating ? 'wait' : 'pointer',
              }}
            >
              {validating ? (
                <>
                  <RefreshCw size={14} className="spin" /> Validating...
                </>
              ) : (
                <>
                  <ShieldCheck size={14} /> Validate Telemetry
                </>
              )}
            </button>
          </div>
        </section>

        {/* Right Column: Validation Response */}
        <section
          className="surface-panel"
          style={{
            background: 'var(--ops-surface)',
            border: '1px solid var(--ops-stroke)',
            borderRadius: '12px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '14px', margin: 0, color: '#f1edfc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={16} color="#4ade80" /> Interoperability Validation Results
            </h3>
            {validationResult && (
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  background:
                    validationResult.status === 'compatible'
                      ? 'rgba(74, 222, 128, 0.15)'
                      : validationResult.status === 'compatible_with_normalization'
                      ? 'rgba(56, 189, 248, 0.15)'
                      : 'rgba(239, 68, 68, 0.15)',
                  color:
                    validationResult.status === 'compatible'
                      ? '#4ade80'
                      : validationResult.status === 'compatible_with_normalization'
                      ? '#38bdf8'
                      : '#f87171',
                  border: `1px solid ${
                    validationResult.status === 'compatible'
                      ? 'rgba(74, 222, 128, 0.3)'
                      : validationResult.status === 'compatible_with_normalization'
                      ? 'rgba(56, 189, 248, 0.3)'
                      : 'rgba(239, 68, 68, 0.3)'
                  }`,
                }}
              >
                {validationResult.status.replaceAll('_', ' ')}
              </span>
            )}
          </div>

          {!validationResult && !validating && (
            <div style={{ flex: 1, display: 'grid', placeContent: 'center', textAlign: 'center', color: '#7f759b', padding: '40px 20px' }}>
              <FileJson size={32} style={{ margin: '0 auto 10px', opacity: 0.5 }} />
              <b style={{ color: '#a49bbd' }}>Awaiting Telemetry Validation</b>
              <p style={{ fontSize: '12px', marginTop: '4px' }}>
                Load a sample payload or paste custom telemetry, then click "Validate Telemetry".
              </p>
            </div>
          )}

          {validating && (
            <div style={{ flex: 1, display: 'grid', placeContent: 'center', textAlign: 'center', color: '#a49bbd', padding: '40px 20px' }}>
              <RefreshCw size={28} className="spin" style={{ margin: '0 auto 10px', color: '#818cf8' }} />
              <b>Evaluating Telemetry Interoperability...</b>
            </div>
          )}

          {validationResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', overflowY: 'auto' }}>
              {/* Header metrics */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                <div style={{ background: '#151020', padding: '8px', borderRadius: '6px', border: '1px solid rgba(152, 134, 203, 0.1)' }}>
                  <small style={{ fontSize: '10px', color: '#7f759b', display: 'block' }}>SCHEMA VERSION</small>
                  <b style={{ fontSize: '13px', color: '#f1edfc' }}>v{validationResult.schema_version}</b>
                </div>
                <div style={{ background: '#151020', padding: '8px', borderRadius: '6px', border: '1px solid rgba(152, 134, 203, 0.1)' }}>
                  <small style={{ fontSize: '10px', color: '#7f759b', display: 'block' }}>ALIASES FOUND</small>
                  <b style={{ fontSize: '13px', color: '#38bdf8' }}>{validationResult.recognized_aliases?.length || 0}</b>
                </div>
                <div style={{ background: '#151020', padding: '8px', borderRadius: '6px', border: '1px solid rgba(152, 134, 203, 0.1)' }}>
                  <small style={{ fontSize: '10px', color: '#7f759b', display: 'block' }}>CONVERSIONS</small>
                  <b style={{ fontSize: '13px', color: '#4ade80' }}>{validationResult.unit_conversions?.length || 0}</b>
                </div>
              </div>

              {/* Errors if any */}
              {validationResult.errors?.length > 0 && (
                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '10px 12px' }}>
                  <b style={{ fontSize: '12px', color: '#f87171', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ShieldAlert size={14} /> Incompatibility Issues ({validationResult.errors.length})
                  </b>
                  <ul style={{ margin: '6px 0 0 16px', padding: 0, fontSize: '11px', color: '#fca5a5', lineHeight: '1.5' }}>
                    {validationResult.errors.map((err, i) => (
                      <li key={i}>
                        <strong>{err.error_type}</strong>
                        {err.field ? ` [${err.field}]` : ''}: {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Missing Required Fields if any */}
              {validationResult.missing_required_fields?.length > 0 && (
                <div style={{ background: 'rgba(234, 178, 108, 0.12)', border: '1px solid rgba(234, 178, 108, 0.35)', borderRadius: '8px', padding: '10px 12px' }}>
                  <b style={{ fontSize: '12px', color: '#eab26c', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertTriangle size={14} /> Missing Required Fields ({validationResult.missing_required_fields.length})
                  </b>
                  <div style={{ marginTop: '6px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {validationResult.missing_required_fields.map((field, i) => (
                      <span key={i} style={{ background: 'rgba(234, 178, 108, 0.2)', color: '#fde68a', fontSize: '11px', padding: '2px 8px', borderRadius: '4px', fontFamily: "'Fira Code', monospace" }}>
                        {field}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Recognized Aliases & Mappings */}
              {validationResult.field_mappings?.length > 0 && (
                <div style={{ background: '#151020', border: '1px solid rgba(152, 134, 203, 0.15)', borderRadius: '8px', padding: '10px 12px' }}>
                  <b style={{ fontSize: '11px', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Recognized Field Aliases ({validationResult.field_mappings.length})
                  </b>
                  <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {validationResult.field_mappings.map((m, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', padding: '3px 6px', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                        <code style={{ color: '#fca5a5' }}>{m.original_field}</code>
                        <ArrowRight size={11} color="#94a3b8" />
                        <code style={{ color: '#4ade80' }}>{m.canonical_field}</code>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Unit conversions */}
              {validationResult.unit_conversions?.length > 0 && (
                <div style={{ background: '#151020', border: '1px solid rgba(152, 134, 203, 0.15)', borderRadius: '8px', padding: '10px 12px' }}>
                  <b style={{ fontSize: '11px', color: '#4ade80', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Applied Unit Conversions ({validationResult.unit_conversions.length})
                  </b>
                  <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {validationResult.unit_conversions.map((u, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', padding: '3px 6px', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                        <span>
                          <b>{u.field}</b>: <code style={{ color: '#fca5a5' }}>{u.original_value}</code>
                        </span>
                        <ArrowRight size={11} color="#94a3b8" />
                        <code style={{ color: '#4ade80' }}>
                          {u.canonical_value} {u.canonical_unit}
                        </code>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Normalized JSON Payload */}
              {validationResult.normalized_payload && (
                <details style={{ background: '#151020', border: '1px solid rgba(152, 134, 203, 0.15)', borderRadius: '8px', padding: '8px 12px' }}>
                  <summary style={{ cursor: 'pointer', fontSize: '11px', color: '#c4b5fd', fontWeight: 600 }}>
                    Inspect Canonical Normalized JSON Payload
                  </summary>
                  <pre
                    style={{
                      marginTop: '8px',
                      background: '#090811',
                      padding: '8px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontFamily: "'Fira Code', monospace",
                      color: '#a49bbd',
                      overflowX: 'auto',
                      maxHeight: '220px',
                    }}
                  >
                    {JSON.stringify(validationResult.normalized_payload, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          )}
        </section>
      </div>

      <footer className="dashboard-footnote">
        <span>
          <i /> INTEROPERABILITY ENGINE · PHASE 3 VERIFIED
        </span>
        <span>NetCoop AI · Canonical Schema & Unit Normalization</span>
      </footer>
    </div>
  )
}
