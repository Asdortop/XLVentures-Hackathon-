'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useApp } from '../layout'

export default function InteractPage() {
  const { domain } = useApp()
  const router = useRouter()
  const [entityName, setEntityName] = useState('')
  const [text, setText] = useState('')
  const [scenarios, setScenarios] = useState<any[]>([])
  const [placeholder, setPlaceholder] = useState('Paste customer interaction here...')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!domain) return
    fetch(`/api/domains/${domain.id}/demo`).then(r => r.json()).then(d => {
      setEntityName(d.entity_name || '')
      setText(d.text || '')
      setPlaceholder(d.placeholder || 'Paste customer interaction here...')
      setScenarios(d.sample_scenarios || [])
    }).catch(() => {})
  }, [domain])

  const handleScenario = (s: any) => {
    setEntityName(s.entity_name)
    setText(s.text)
  }

  const handleSubmit = async () => {
    if (!domain || !text.trim() || !entityName.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/interactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain_id: domain.id, entity_name: entityName, text }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      router.push(`/nba/${data.nba_id}`)
    } catch (e: any) {
      setError(e.message || 'Submission failed')
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <div className="page-header">
        <div className="page-title">Submit Interaction</div>
        <div className="page-subtitle">Paste a customer signal — the agent pipeline will analyze and return ranked Next Best Actions</div>
      </div>

      {/* Pipeline mini-banner */}
      <div className="card" style={{ marginBottom: 28, padding: '14px 20px', background: 'linear-gradient(135deg, rgba(99,102,241,0.06), rgba(168,85,247,0.06))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
          <span>Your input will flow through:</span>
          {['Planner', 'Context', 'Dependency', 'Risk', 'Recommender'].map((a, i, arr) => (
            <span key={a} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: 'var(--indigo-light)', fontWeight: 600 }}>{a}</span>
              {i < arr.length - 1 && <span style={{ color: 'var(--text-muted)' }}>→</span>}
            </span>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="form-group">
          <label className="form-label">{domain?.entity_label || 'Entity'} Name *</label>
          <input
            className="form-input"
            value={entityName}
            onChange={e => setEntityName(e.target.value)}
            placeholder={`e.g. Acme Corp, GlobalBank CFO Search...`}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Interaction Text *</label>
          <textarea
            className="form-textarea"
            style={{ minHeight: 160 }}
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder={placeholder}
          />
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
            Meeting notes, CRM updates, emails, chat messages — any signal about this {domain?.entity_label?.toLowerCase() || 'entity'}
          </div>
        </div>

        {/* Sample scenarios */}
        {scenarios.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Or try a sample:</div>
            <div className="scenario-chips">
              {scenarios.map((s, i) => (
                <button key={i} className="chip" onClick={() => handleScenario(s)}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-md)', fontSize: 13, color: 'var(--red)', marginBottom: 16 }}>
            {error}
          </div>
        )}

        <button
          className="btn btn-primary btn-lg"
          onClick={handleSubmit}
          disabled={loading || !text.trim() || !entityName.trim() || !domain}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {loading ? (
            <><span className="spinner" /> Running agent pipeline...</>
          ) : (
            <>✦ Analyze &amp; Generate Recommendations</>
          )}
        </button>
      </div>
    </div>
  )
}
