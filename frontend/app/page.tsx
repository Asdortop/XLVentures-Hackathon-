'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useApp } from './context'

export default function CommandCenter() {
  const { domain } = useApp()
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
    <div className="empty-state">
      <div className="empty-icon">⬡</div>
      <div className="empty-title">No Domain Selected</div>
      <div className="empty-desc">Select a domain from the sidebar or <Link href="/onboarding" style={{ color: 'var(--indigo-light)' }}>onboard a new company</Link></div>
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
