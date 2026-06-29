'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useApp } from '../layout'

export default function NBAInbox() {
  const { domain } = useApp()
  const [nbas, setNbas] = useState<any[]>([])
  const [filter, setFilter] = useState('pending')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!domain) return
    setLoading(true)
    fetch(`/api/nba/${domain.id}?status=${filter}`).then(r => r.json()).then(d => {
      setNbas(d)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [domain, filter])

  const sevColor = (s: string) => ({ critical: 'var(--sev-critical)', high: '#f97316', medium: 'var(--sev-medium)', low: 'var(--sev-low)' }[s] || 'var(--text-secondary)')

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div className="page-title">NBA Inbox</div>
          <div className="page-subtitle">Review and approve next best actions — all recommendations require human sign-off</div>
        </div>
        <Link href="/interact"><button className="btn btn-primary">✦ New Interaction</button></Link>
      </div>

      <div className="tabs">
        {['pending', 'approved', 'rejected'].map(s => (
          <button key={s} className={`tab ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading-overlay"><div className="spinner" /><span>Loading...</span></div>
      ) : nbas.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">◈</div>
          <div className="empty-title">No {filter} NBAs</div>
          <div className="empty-desc">
            {filter === 'pending' ? <><Link href="/interact" style={{ color: 'var(--indigo-light)' }}>Submit an interaction</Link> to generate recommendations.</> : `No ${filter} recommendations yet.`}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {nbas.map(n => (
            <Link key={n.id} href={`/nba/${n.id}`}>
              <div className="nba-card">
                <div style={{ width: 4, height: 48, borderRadius: 2, background: sevColor(n.severity), flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div className="nba-entity">{n.entity_name}</div>
                  <div className="nba-meta">
                    {n.action_count} recommended actions · Intent: <span style={{ color: 'var(--indigo-light)' }}>{n.matched_intent}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                    {n.interaction_text}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                  <span className={`badge badge-${n.severity}`}>{n.severity}</span>
                  <span className="confidence-pill">{Math.round(n.top_confidence * 100)}% confidence</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{new Date(n.created_at).toLocaleString()}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
