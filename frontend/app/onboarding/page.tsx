'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

type Step = 'intake' | 'generating' | 'blueprint' | 'deployed'

const TEMPLATE_SAAS = {
  company_name: 'Meridian SaaS', industry: 'SaaS',
  what_they_manage: 'We manage enterprise software subscriptions and customer success for 200+ accounts',
  decisions: 'Whether to schedule a QBR, escalate a churn risk, send a renewal proposal, or expand an account',
  primary_entity: 'Account',
  sops_text: 'When health score drops below 65%, schedule QBR within 5 days. When renewal is within 30 days, send proposal. When NPS < 6, escalate to director.',
  rules_text: 'Health score < 60 = critical. Renewal within 30 days = high. 3 missed check-ins = escalate.',
  actions_text: 'Schedule QBR, Send renewal proposal, Escalate to CSM director, Flag for health intervention, Prepare expansion pitch'
}

const TEMPLATE_LEGAL = {
  company_name: 'LexOps Legal', industry: 'Legal',
  what_they_manage: 'We manage legal cases, client relationships, and court deadlines for enterprise clients',
  decisions: 'Whether to file documents, schedule hearings, escalate to senior partner, or flag billing issues',
  primary_entity: 'Case',
  sops_text: 'Court deadlines must be filed 48 hours in advance. Client without contact for 2 weeks = urgent check-in. Billing disputes > 30 days = escalate.',
  rules_text: 'Deadline within 48 hours = critical. Unanswered client for 14 days = high. Billing > 30 days = medium.',
  actions_text: 'File court documents, Schedule client meeting, Escalate to senior partner, Send billing statement, Request extension'
}

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>('intake')
  const [form, setForm] = useState({
    company_name: '', industry: 'SaaS', what_they_manage: '', decisions: '',
    primary_entity: 'Account', sops_text: '', rules_text: '', actions_text: '', crm_sample: ''
  })
  const [preview, setPreview] = useState<any>(null)
  const [rawFiles, setRawFiles] = useState<any>(null)
  const [slug, setSlug] = useState('')
  const [error, setError] = useState('')
  const [genAttempts, setGenAttempts] = useState(0)
  const [toast, setToast] = useState('')

  const applyTemplate = (t: any) => setForm(f => ({ ...f, ...t }))

  const handleGenerate = async () => {
    if (!form.company_name.trim()) { setError('Company name is required'); return }
    setStep('generating')
    setError('')
    try {
      const res = await fetch('/api/onboarding/configure', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form)
      })
      if (!res.ok) {
        const e = await res.json()
        throw new Error(e.detail || 'Generation failed')
      }
      const data = await res.json()
      setPreview(data.preview)
      setRawFiles(data.raw_files)
      setSlug(data.slug)
      setGenAttempts(data.attempts)
      setStep('blueprint')
    } catch (e: any) {
      setError(e.message)
      setStep('intake')
    }
  }

  const handleDeploy = async () => {
    try {
      const res = await fetch('/api/onboarding/confirm', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, company_name: form.company_name, industry: form.industry, files: rawFiles })
      })
      if (!res.ok) throw new Error('Deploy failed')
      setStep('deployed')
      setTimeout(() => router.push('/'), 2500)
    } catch (e: any) {
      setError(e.message)
    }
  }

  const healthScore = () => {
    if (!preview) return 0
    let score = 0
    if (preview.entities?.length > 0) score += 20
    if (preview.intents?.length >= 2) score += 20
    if (preview.actions?.length >= 2) score += 20
    if (preview.knowledge_sources?.length > 0) score += 20
    if (form.sops_text?.length > 50) score += 20
    return score
  }

  const hs = healthScore()
  const hsColor = hs >= 80 ? 'var(--emerald)' : hs >= 60 ? 'var(--amber)' : 'var(--red)'

  return (
    <div style={{ maxWidth: 1100 }}>
      <div className="page-header">
        <div className="page-title">Blueprint Studio</div>
        <div className="page-subtitle">Self-configure your domain adapter in minutes — paste your knowledge, generate your agent pipeline</div>
      </div>

      {/* Step indicator */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 28 }}>
        {[['intake', '1', 'Business Profile'], ['generating', '2', 'Generating'], ['blueprint', '3', 'Blueprint Canvas'], ['deployed', '4', 'Deployed']].map(([s, num, label], i, arr) => (
          <div key={s} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderRadius: 'var(--radius-md)', background: step === s ? 'var(--indigo-dim)' : 'transparent', border: step === s ? '1px solid rgba(99,102,241,0.4)' : '1px solid transparent' }}>
              <div style={{ width: 22, height: 22, borderRadius: '50%', background: step === s ? 'var(--indigo)' : 'var(--bg-elevated)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700 }}>{num}</div>
              <span style={{ fontSize: 13, fontWeight: 600, color: step === s ? 'var(--indigo-light)' : 'var(--text-muted)' }}>{label}</span>
            </div>
            {i < arr.length - 1 && <div style={{ width: 24, height: 1, background: 'var(--border)' }} />}
          </div>
        ))}
      </div>

      {/* STEP: Intake */}
      {step === 'intake' && (
        <div className="grid-cols-2-3">
          <div>
            <div className="section-title">Company Info</div>
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="form-group">
                <label className="form-label">Company Name *</label>
                <input className="form-input" value={form.company_name} onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))} placeholder="e.g. TalentBridge Staffing" />
              </div>
              <div className="form-group">
                <label className="form-label">Industry</label>
                <select className="form-select" value={form.industry} onChange={e => setForm(f => ({ ...f, industry: e.target.value }))}>
                  {['SaaS', 'Staffing', 'Legal', 'Construction', 'Healthcare', 'Finance', 'Retail', 'Other'].map(i => <option key={i}>{i}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">What does your team manage?</label>
                <textarea className="form-textarea" style={{ minHeight: 70 }} value={form.what_they_manage} onChange={e => setForm(f => ({ ...f, what_they_manage: e.target.value }))} placeholder="e.g. We manage enterprise client accounts and their software renewals..." />
              </div>
              <div className="form-group">
                <label className="form-label">What decisions do you make daily?</label>
                <textarea className="form-textarea" style={{ minHeight: 70 }} value={form.decisions} onChange={e => setForm(f => ({ ...f, decisions: e.target.value }))} placeholder="e.g. Whether to escalate, book a meeting, send a proposal..." />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Primary entity name</label>
                <input className="form-input" value={form.primary_entity} onChange={e => setForm(f => ({ ...f, primary_entity: e.target.value }))} placeholder="Account / Candidate / Case / Project" />
              </div>
            </div>

            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Start from a template:</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="chip" onClick={() => applyTemplate(TEMPLATE_SAAS)}>SaaS CSM</button>
              <button className="chip" onClick={() => applyTemplate(TEMPLATE_LEGAL)}>Legal Ops</button>
            </div>
          </div>

          <div>
            <div className="section-title">Your Business Knowledge</div>
            <div className="card">
              <div className="form-group">
                <label className="form-label">📋 SOPs & Playbooks</label>
                <textarea className="form-textarea" style={{ minHeight: 100 }} value={form.sops_text} onChange={e => setForm(f => ({ ...f, sops_text: e.target.value }))} placeholder="When a client rejects 3 candidates, escalate to director. When health score drops below 60%, initiate QBR within 5 days..." />
              </div>
              <div className="form-group">
                <label className="form-label">⚠️ Business Rules & Urgency</label>
                <textarea className="form-textarea" style={{ minHeight: 80 }} value={form.rules_text} onChange={e => setForm(f => ({ ...f, rules_text: e.target.value }))} placeholder="Renewal within 30 days = high priority. Three rejections = critical. Deadline within 48 hours = escalate..." />
              </div>
              <div className="form-group">
                <label className="form-label">✦ Available Actions</label>
                <textarea className="form-textarea" style={{ minHeight: 80 }} value={form.actions_text} onChange={e => setForm(f => ({ ...f, actions_text: e.target.value }))} placeholder="Schedule executive review, Send proposal, Escalate to director, Source premium candidates..." />
              </div>
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">◈ Sample CRM Data (optional)</label>
                <textarea className="form-textarea" style={{ minHeight: 60 }} value={form.crm_sample} onChange={e => setForm(f => ({ ...f, crm_sample: e.target.value }))} placeholder="GlobalBank - 50 open reqs, renewal in 30 days, tier: enterprise" />
              </div>

              {error && <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-md)', fontSize: 13, color: 'var(--red)', marginBottom: 16 }}>{error}</div>}

              <button className="btn btn-primary btn-lg" onClick={handleGenerate} style={{ width: '100%', justifyContent: 'center' }}>
                ⊕ Generate Blueprint
              </button>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', marginTop: 8 }}>
                Self-healing generation loop · Up to 3 validation attempts · Auto-deploys on success
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STEP: Generating */}
      {step === 'generating' && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 80 }}>
          <div style={{ position: 'relative', width: 80, height: 80, marginBottom: 24 }}>
            <div className="spinner" style={{ width: 80, height: 80, borderWidth: 3 }} />
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28 }}>⬡</div>
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Generating Blueprint</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 14, textAlign: 'center', maxWidth: 400 }}>
            Parsing your business knowledge → Generating YAML → Validating schema → Auto-fixing errors...
          </div>
          <div className="pipeline-flow" style={{ marginTop: 24, justifyContent: 'center' }}>
            {['Parse', 'Generate', 'Validate', 'Auto-Fix', 'Deploy'].map((s, i, arr) => (
              <span key={s} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                <span style={{ color: 'var(--indigo-light)', fontWeight: 600 }}>{s}</span>
                {i < arr.length - 1 && <span style={{ color: 'var(--text-muted)' }}>→</span>}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* STEP: Blueprint Canvas */}
      {step === 'blueprint' && preview && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>Blueprint Generated ✓</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {genAttempts > 1 ? `⚡ Self-healed in ${genAttempts} attempts` : '✓ Generated in 1 attempt'} · Review and deploy
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-ghost" onClick={() => setStep('intake')}>← Edit</button>
              <button className="btn btn-primary btn-lg" onClick={handleDeploy}>⊕ Deploy Domain →</button>
            </div>
          </div>

          {/* Health Score */}
          <div className="health-bar" style={{ marginBottom: 20 }}>
            <div className="health-bar-label">
              <span>Blueprint Health</span>
              <span style={{ color: hsColor, fontWeight: 700 }}>{hs}%</span>
            </div>
            <div className="health-track">
              <div className="health-fill" style={{ width: `${hs}%`, background: `linear-gradient(90deg, var(--indigo), ${hsColor})` }} />
            </div>
            <div className="health-items">
              {[
                { ok: preview.entities?.length > 0, label: 'Entities defined' },
                { ok: preview.intents?.length >= 2, label: `${preview.intents?.length} intents` },
                { ok: preview.actions?.length >= 2, label: `${preview.actions?.length} actions` },
                { ok: preview.knowledge_sources?.length > 0, label: 'Knowledge sources' },
                { ok: form.sops_text?.length > 50, label: 'SOPs provided' },
              ].map((item, i) => (
                <div key={i} className="health-item">
                  <div className="health-item-dot" style={{ background: item.ok ? 'var(--emerald)' : 'var(--red)' }} />
                  <span style={{ fontSize: 11, color: item.ok ? 'var(--text-secondary)' : 'var(--red)' }}>{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Blueprint Canvas */}
          <div className="blueprint-canvas">
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Blueprint Canvas — {form.company_name}
            </div>

            <div className="blueprint-section">
              <div className="blueprint-section-title">Entities</div>
              {preview.entities?.map((e: any) => (
                <span key={e.id} className="blueprint-node node-entity">⬡ {e.label}{e.primary ? ' (primary)' : ''}</span>
              ))}
            </div>

            <div className="blueprint-section">
              <div className="blueprint-section-title">Intents ({preview.intents?.length})</div>
              {preview.intents?.map((i: any) => (
                <span key={i.id} className="blueprint-node node-intent" title={i.keywords?.join(', ')}>◈ {i.label}</span>
              ))}
            </div>

            <div className="blueprint-section">
              <div className="blueprint-section-title">Actions ({preview.actions?.length})</div>
              {preview.actions?.map((a: any) => (
                <span key={a.id} className="blueprint-node node-action" title={`Owner: ${a.owner} · Priority: ${a.priority} · Confidence: ${Math.round((a.base_confidence || 0) * 100)}%`}>
                  ★ {a.action?.slice(0, 50)}{a.action?.length > 50 ? '...' : ''}
                </span>
              ))}
            </div>

            <div className="blueprint-section">
              <div className="blueprint-section-title">Business Rules</div>
              {Object.entries(preview.rules?.severity_keywords || {}).map(([sev, kws]: [string, any]) => (
                <span key={sev} className="blueprint-node node-rule">◎ {sev}: {Array.isArray(kws) ? kws.slice(0, 3).join(', ') : String(kws)}</span>
              ))}
            </div>

            <div className="blueprint-section" style={{ marginBottom: 0 }}>
              <div className="blueprint-section-title">Knowledge Sources ({preview.knowledge_sources?.length})</div>
              {preview.knowledge_sources?.map((k: any) => (
                <span key={k.id} className="blueprint-node node-knowledge" title={k.excerpt}>📘 {k.title}</span>
              ))}
            </div>
          </div>

          {error && <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-md)', fontSize: 13, color: 'var(--red)', marginTop: 16 }}>{error}</div>}
        </div>
      )}

      {/* STEP: Deployed */}
      {step === 'deployed' && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 80 }}>
          <div style={{ fontSize: 64, marginBottom: 20 }}>✓</div>
          <div style={{ fontSize: 24, fontWeight: 800, marginBottom: 8, color: 'var(--emerald)' }}>Domain Deployed!</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>{form.company_name} is now live. Redirecting to Command Center...</div>
        </div>
      )}
    </div>
  )
}
