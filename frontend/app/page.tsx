'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useApp } from './context'

export default function CommandCenter() {
  const { domain, domains } = useApp()
  const [outcomes, setOutcomes] = useState<any>(null)
  const [interactions, setInteractions] = useState<any[]>([])
  const [recentNBAs, setRecentNBAs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!domain) return
    setLoading(true)
    Promise.all([
      fetch(`/api/outcomes/${domain.id}`).then(r => r.json()),
      fetch(`/api/interactions/${domain.id}`).then(r => r.json()),
      fetch(`/api/nba/${domain.id}`).then(r => r.json()),
    ]).then(([o, i, n]) => {
      setOutcomes(o)
      setInteractions(i.slice(0, 5))
      setRecentNBAs(n.slice(0, 5))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [domain])

  const sevColor = (s: string) => ({ critical: 'var(--sev-critical)', high: '#f97316', medium: 'var(--sev-medium)', low: 'var(--sev-low)' }[s] || 'var(--text-secondary)')

  if (!domain) return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '48px 24px', textAlign: 'center' }}>

      {/* Hero */}
      <div style={{ fontSize: 52, marginBottom: 20, filter: 'drop-shadow(0 0 24px rgba(99,102,241,0.5))' }}>⬡</div>
      <h1 style={{ fontSize: 32, fontWeight: 800, background: 'linear-gradient(135deg, #fff 30%, var(--indigo-light))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: 12, lineHeight: 1.2 }}>
        Welcome to Praxis AI
      </h1>
      <p style={{ fontSize: 14, color: 'var(--indigo-light)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 20, fontWeight: 600 }}>
        Agentic Decision Intelligence
      </p>
      <p style={{ fontSize: 15, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 520, margin: '0 auto 40px', }}>
        Paste any business signal — a meeting note, email, or CRM update — and six AI agents
        reason over it live to give you ranked, evidence-backed Next Best Actions.
        The platform learns from every decision your team makes.
      </p>

      {/* Flow Chart */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0, marginBottom: 48, flexWrap: 'wrap' }}>
        {[
          { step: '01', label: 'Add Domain', icon: '⊕', desc: 'Describe your business' },
          { step: '02', label: 'Submit Signal', icon: '✦', desc: 'Paste any interaction' },
          { step: '03', label: '6 Agents Run', icon: '⬡', desc: 'Live reasoning pipeline' },
          { step: '04', label: 'Review NBA', icon: '★', desc: 'Approve or reject' },
        ].map((item, i, arr) => (
          <div key={item.step} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{
              background: 'rgba(99,102,241,0.08)',
              border: '1px solid rgba(99,102,241,0.25)',
              borderRadius: 12,
              padding: '16px 20px',
              minWidth: 120,
              transition: 'border-color 0.2s',
            }}>
              <div style={{ fontSize: 20, marginBottom: 6 }}>{item.icon}</div>
              <div style={{ fontSize: 11, color: 'var(--indigo-light)', fontWeight: 700, letterSpacing: '0.08em', marginBottom: 4 }}>{item.step}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>{item.label}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.desc}</div>
            </div>
            {i < arr.length - 1 && (
              <div style={{ padding: '0 8px', color: 'var(--indigo-light)', fontSize: 18, opacity: 0.6 }}>→</div>
            )}
          </div>
        ))}
      </div>

      {/* Memory callout */}
      <div style={{ background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.18)', borderRadius: 10, padding: '14px 24px', marginBottom: 36, fontSize: 13, color: 'var(--text-secondary)', display: 'inline-block' }}>
        🧠 <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Memory learns over time</span> — every approval and rejection improves future recommendations
      </div>

      {/* CTA */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <Link href="/onboarding">
          <button className="btn btn-primary" style={{ fontSize: 15, padding: '12px 28px' }}>⊕ Add Your Domain →</button>
        </Link>
        {domains.length > 0 && (
          <button className="btn btn-ghost" onClick={() => {}} style={{ fontSize: 14 }}>
            or select from sidebar
          </button>
        )}
      </div>
    </div>
  )


  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div className="page-title">Command Center</div>
          <div className="page-subtitle">{domain.label} · {domain.entity_label} Management</div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Link href="/interact"><button className="btn btn-primary">✦ Submit Interaction</button></Link>
          <Link href="/nba"><button className="btn btn-ghost">◈ NBA Inbox {outcomes?.pending > 0 && <span className="nav-badge">{outcomes.pending}</span>}</button></Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid-4" style={{ marginBottom: 28 }}>
        <div className="stat-card">
          <div className="stat-value">{loading ? '—' : outcomes?.total_nbas ?? 0}</div>
          <div className="stat-label">Decisions Processed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ background: 'linear-gradient(135deg, var(--emerald), var(--cyan))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {loading ? '—' : `${Math.round((outcomes?.approval_rate ?? 0) * 100)}%`}
          </div>
          <div className="stat-label">Approval Rate</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ background: 'linear-gradient(135deg, var(--purple), var(--indigo-light))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {loading ? '—' : (outcomes?.semantic_memory_count ?? 0) + (outcomes?.pattern_count ?? 0)}
          </div>
          <div className="stat-label">Memory Items</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ background: 'linear-gradient(135deg, var(--amber), var(--red))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {loading ? '—' : outcomes?.pending ?? 0}
          </div>
          <div className="stat-label">Pending Review</div>
        </div>
      </div>

      {/* Pipeline Architecture Banner */}
      <div className="card" style={{ marginBottom: 28, background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(168,85,247,0.08))', borderColor: 'rgba(99,102,241,0.25)' }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Active Agent Pipeline</div>
        <div className="pipeline-flow">
          {['✦ Planner', '◈ Context', '⬡ Dependency', '◎ Risk', '★ Recommender', '⚑ Critic'].map((step, i, arr) => (
            <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="flow-node">{step}</div>
              {i < arr.length - 1 && <span className="flow-arrow">→</span>}
            </div>
          ))}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
          Every interaction flows through all 6 agents · Evidence-backed recommendations · HITL before any action
        </div>
      </div>

      <div className="grid-2">
        {/* Recent Interactions */}
        <div>
          <div className="section-title">◈ Recent Interactions</div>
          {interactions.length === 0 && !loading ? (
            <div className="card-sm" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
              No interactions yet. <Link href="/interact" style={{ color: 'var(--indigo-light)' }}>Submit one →</Link>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {interactions.map(i => (
                <Link key={i.id} href={i.nba_id ? `/nba/${i.nba_id}` : '/nba'}>
                  <div className="card-sm" style={{ cursor: 'pointer', transition: 'border-color 0.2s' }} onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-bright)')} onMouseLeave={e => (e.currentTarget.style.borderColor = '')}>
                    <div style={{ fontWeight: 700, fontSize: 13 }}>{i.entity_name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{i.text}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>{new Date(i.created_at).toLocaleString()}</div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent NBAs */}
        <div>
          <div className="section-title">★ Recent NBAs</div>
          {recentNBAs.length === 0 && !loading ? (
            <div className="card-sm" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
              No recommendations yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {recentNBAs.map(n => (
                <Link key={n.id} href={`/nba/${n.id}`}>
                  <div className="nba-card">
                    <div style={{ flex: 1 }}>
                      <div className="nba-entity">{n.entity_name}</div>
                      <div className="nba-meta">{n.action_count} actions · Intent: {n.matched_intent}</div>
                    </div>
                    <span className={`badge badge-${n.severity}`}>{n.severity}</span>
                    <span className={`badge badge-${n.hitl_status}`}>{n.hitl_status}</span>
                    <span className="confidence-pill">{Math.round(n.top_confidence * 100)}%</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
