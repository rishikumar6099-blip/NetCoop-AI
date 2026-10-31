export const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '')

export class DiagnosisApiError extends Error {
  constructor(message, { kind = 'unexpected', status = null, body = null, cause = null } = {}) {
    super(message, { cause })
    this.name = 'DiagnosisApiError'
    this.kind = kind
    this.status = status
    this.body = body
  }
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

const performanceNumbers = ['latency_ms', 'jitter_ms', 'packet_loss_pct', 'throughput_mbps', 'link_utilization_pct']
const infrastructureNumbers = ['cpu_utilization_pct', 'memory_utilization_pct', 'interface_errors', 'egress_queue_drops']

function serializeSample(sample, numericFields, integerFields = []) {
  const result = { device_id: sample.device_id.trim() }
  if (sample.interface_id.trim()) result.interface_id = sample.interface_id.trim()
  for (const field of numericFields) {
    const value = sample[field]
    if (value !== '') result[field] = integerFields.includes(field) ? Number.parseInt(value, 10) : Number(value)
  }
  if ('device_status' in sample && sample.device_status) result.device_status = sample.device_status
  return result
}

export function buildDiagnosisRequest({ diagnosisId, performanceSamples, infrastructureSamples, devices, links }) {
  return {
    performance: {
      diagnosis_id: diagnosisId,
      samples: performanceSamples.map((sample) => serializeSample(sample, performanceNumbers)),
    },
    infrastructure: {
      diagnosis_id: diagnosisId,
      samples: infrastructureSamples.map((sample) => serializeSample(
        sample,
        infrastructureNumbers,
        ['interface_errors', 'egress_queue_drops'],
      )),
    },
    connectivity: {
      diagnosis_id: diagnosisId,
      devices: devices.map((device) => {
        const result = { device_id: device.device_id.trim() }
        if (device.segment_id.trim()) result.segment_id = device.segment_id.trim()
        if (device.reachability) result.reachability = device.reachability
        return result
      }),
      links: links.map((link) => ({
        link_id: link.link_id.trim(),
        source_device_id: link.source_device_id.trim(),
        target_device_id: link.target_device_id.trim(),
        status: link.status || 'unknown',
      })),
    },
  }
}

function validateDiagnosisResponse(body, diagnosisId) {
  if (
    !isObject(body) ||
    typeof body.diagnosis_id !== 'string' ||
    !['complete', 'partial'].includes(body.status) ||
    !isObject(body.agent_messages) ||
    !Array.isArray(body.failures)
  ) {
    throw new DiagnosisApiError('The backend returned a response with an unexpected shape.', {
      kind: 'unexpected',
      status: 200,
      body,
    })
  }

  if (body.diagnosis_id !== diagnosisId) {
    throw new DiagnosisApiError('The backend response diagnosis ID does not match the submitted request.', {
      kind: 'unexpected',
      status: 200,
      body,
    })
  }

  const expectedAgents = ['performance', 'infrastructure', 'connectivity']
  const agentEntries = Object.entries(body.agent_messages)
  if (agentEntries.some(([name, message]) => !expectedAgents.includes(name) || !isObject(message))) {
    throw new DiagnosisApiError('The backend returned an invalid agent_messages object.', {
      kind: 'unexpected',
      status: 200,
      body,
    })
  }

  if (body.status === 'complete' && (
    expectedAgents.some((name) => !isObject(body.agent_messages[name])) ||
    !isObject(body.correlation_result) ||
    !isObject(body.diagnostic_report)
  )) {
    throw new DiagnosisApiError('The backend marked the workflow complete but omitted required agent, correlation, or report data.', {
      kind: 'unexpected',
      status: 200,
      body,
    })
  }

  if (body.status === 'partial' && body.failures.length === 0) {
    throw new DiagnosisApiError('The backend marked the workflow partial without reporting a failed stage.', {
      kind: 'unexpected',
      status: 200,
      body,
    })
  }

  return body
}

export async function submitDiagnosis(request, { signal } = {}) {
  if (!isObject(request) || !isObject(request.performance) || typeof request.performance.diagnosis_id !== 'string') {
    throw new DiagnosisApiError('The diagnosis request is missing its performance section or diagnosis ID.', {
      kind: 'unexpected',
    })
  }

  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/diagnose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(request),
      signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') throw error
    const targetDesc = API_BASE_URL ? ` at ${API_BASE_URL}` : ' on 127.0.0.1:8000'
    throw new DiagnosisApiError(
      `Could not connect to the NetCoop AI backend${targetDesc}. Check that the FastAPI service is active.`,
      { kind: 'connection', cause: error },
    )
  }

  const rawBody = await response.text()
  const proxyConnectionFailure =
    [502, 503, 504].includes(response.status) ||
    (response.status >= 500 && /http proxy error|proxy error|ECONNREFUSED|connect ECONN|failed to proxy/i.test(rawBody))
  let body = null
  if (rawBody) {
    try {
      body = JSON.parse(rawBody)
    } catch (error) {
      if (proxyConnectionFailure) {
        throw new DiagnosisApiError('The Vite proxy could not connect to the FastAPI backend. Check that it is running on 127.0.0.1:8000.', {
          kind: 'connection', status: response.status, body: rawBody, cause: error,
        })
      }
      if (response.status === 422) {
        throw new DiagnosisApiError('The backend rejected the request with HTTP 422 but returned unreadable validation details.', {
          kind: 'validation', status: response.status, body: rawBody, cause: error,
        })
      }
      throw new DiagnosisApiError('The backend response was not valid JSON.', {
        kind: 'unexpected', status: response.status, body: rawBody, cause: error,
      })
    }
  }

  if (response.status === 422) {
    throw new DiagnosisApiError('The backend rejected the diagnosis request. Review the field validation details.', {
      kind: 'validation', status: 422, body,
    })
  }

  if (proxyConnectionFailure) {
    throw new DiagnosisApiError('The Vite proxy could not connect to the FastAPI backend. Check that it is running on 127.0.0.1:8000.', {
      kind: 'connection', status: response.status, body,
    })
  }

  if (!response.ok) {
    throw new DiagnosisApiError(`The backend returned HTTP ${response.status}.`, {
      kind: 'http', status: response.status, body,
    })
  }

  if (response.status !== 200 || !body) {
    throw new DiagnosisApiError(`The backend returned an unexpected HTTP ${response.status} response.`, {
      kind: 'unexpected', status: response.status, body,
    })
  }

  return validateDiagnosisResponse(body, request.performance.diagnosis_id)
}

export function describeApiError(error) {
  if (!(error instanceof DiagnosisApiError)) {
    return { kind: 'unexpected', status: null, message: error?.message || 'An unexpected error occurred.', details: [], body: null }
  }

  const issues = Array.isArray(error.body?.detail) ? error.body.detail : []
  const details = issues.map((issue) => {
    const location = Array.isArray(issue.loc) ? issue.loc.filter((part) => part !== 'body').join(' → ') : ''
    return location ? `${location}: ${issue.msg || 'Invalid value'}` : issue.msg || String(issue)
  })

  return {
    kind: error.kind,
    status: error.status,
    message: error.message,
    details,
    body: error.body,
  }
}

export async function checkBackendHealth({ signal } = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, { signal })
    return response.ok
  } catch {
    return false
  }
}

export async function getDiagnosisHistory({ limit = 20, offset = 0 } = {}, { signal } = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/diagnoses?limit=${limit}&offset=${offset}`, {
      headers: { Accept: 'application/json' },
      signal,
    })
    if (!response.ok) {
      throw new DiagnosisApiError(`Failed to fetch history (HTTP ${response.status})`, {
        kind: 'http',
        status: response.status,
      })
    }
    return await response.json()
  } catch (error) {
    if (error instanceof DiagnosisApiError) throw error
    throw new DiagnosisApiError('Failed to retrieve diagnosis history from backend.', {
      kind: 'connection',
      cause: error,
    })
  }
}

export async function getDiagnosisById(diagnosisId, { signal } = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/diagnoses/${encodeURIComponent(diagnosisId)}`, {
      headers: { Accept: 'application/json' },
      signal,
    })
    if (!response.ok) {
      throw new DiagnosisApiError(`Diagnosis '${diagnosisId}' not found (HTTP ${response.status})`, {
        kind: 'http',
        status: response.status,
      })
    }
    return await response.json()
  } catch (error) {
    if (error instanceof DiagnosisApiError) throw error
    throw new DiagnosisApiError(`Failed to retrieve diagnosis '${diagnosisId}'.`, {
      kind: 'connection',
      cause: error,
    })
  }
}

export async function validateInteroperability({ domain, payload, schema_version }, { signal } = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/interop/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ domain, payload, schema_version }),
      signal,
    })
    const body = await response.json()
    return body
  } catch (error) {
    throw new DiagnosisApiError('Interoperability validation failed to connect to backend.', {
      kind: 'connection',
      cause: error,
    })
  }
}

