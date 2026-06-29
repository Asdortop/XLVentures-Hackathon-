'use client'
import { useEffect, useState } from 'react'
import { useApp } from '../layout'

export default function OutcomesPage() {
  const { domain } = useApp()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!domain) return
    fetch(`/api/outcomes/${domain.id}`).then(r => r.json()).then(d => { setData(d); setLoading(false) }).catch(() => setLoading(false))
  }, [domain])

  if (loading) return <div className="loading-overlay"><div className="spinner" /><span>Loading outcomes...</span></div>

  const approvalPct = Math.round((data?.approval_rate ?? 0) * 100)

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Outcomes Dashboard</div>
        <div className="page-subtitle">Measurable impact of {domain?.label} — approval rates, memory growth, value generated</div>
      </div>

      {/* Key Metrics */}
      <div className="grid-4" style={{ marginBottom: 28 }}>
        <div className="stat-card">
          <div className="stat-value">{data?.total_nbas ?? 0}</div>
          <div className="stat-label">Decisions Supported</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ background: 'linear-gradient(135deg,var(--emerald),var(--cyan))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {approvalPct}%
          </div>
          <div className="stat-label">Approval Rate</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>
            {data?.approved} approved · {data?.rejected} rejected
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ background: 'linear-gradient(135deg,var(--purple),var(--indigo-light))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {data?.pattern_count ?? 0}
          </div>
          <div className="stat-label">Memory Patterns</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>Learned from interactions</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ background: 'linear-gradient(135deg,var(--amber),var(--red))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {data?.value_metric?.total > 0 ? `$${(data.value_metric.total / 1000).toFixed(0)}K` : data?.approved ?? 0}
          </div>
          <div className="stat-label">{data?.value_metric?.label || 'Approved Decisions'}</div>
        </div>
      </div>

      <div className="grid-2">
        {/* Approval Rate Visual */}
        <div className="card">
          <div className="section-title">◎ Approval Rate</div>
          <div style={{ position: 'relative', width: 140, height: 140, margin: '0 auto 20px' }}>
            <svg viewBox="0 0 140 140" style={{ transform: 'rotate(-90deg)', width: '100%' }}>
              <circle cx="70" cy="70" r="56" fill="none" stroke="var(--bg-elevated)" strokeWidth="12" />
              <circle cx="70" cy="70" r="56" fill="none" stroke="url(#grad)" strokeWidth="12"
                strokeDasharray={`${approvalPct * 3.52} 352`} strokeLinecap="round" />
              <defs>
                <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="var(--indigo)" />
                  <stop offset="100%" stopColor="var(--emerald)" />
                </linearGradient>
              </defs>
            </svg>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-primary)' }}>{approvalPct}%</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>APPROVAL</div>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 20 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--emerald)' }}>{data?.approved}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Approved</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--red)' }}>{data?.rejected}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Rejected</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--amber)' }}>{data?.pending}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Pending</div>
            </div>
          </div>
        </div>

        {/* Memory Growth */}
        <div className="card">
          <div className="section-title">◈ Top Memory Patterns</div>
          {data?.top_patterns?.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No patterns yet — approve some NBAs to build memory.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {data?.top_patterns?.map((p: any, i: number) => (
                <div key={i} className="card-sm" style={{ padding: '12px 14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--indigo-light)' }}>{p.issue_type}</span>
                    <span style={{ fontSize: 12, color: 'var(--emerald)', fontWeight: 700 }}>{Math.round(p.success_rate * 100)}% success</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{p.resolution.slice(0, 60)}...</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{p.success_count} successful resolutions</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top Actions */}
      {data?.top_actions?.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="section-title">★ Top Performing Actions</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {data.top_actions.map((a: any, i: number) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <div className="action-rank">#{i + 1}</div>
                <div style={{ flex: 1, fontSize: 13 }}>{a.action}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 80, height: 6, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${a.approval_rate * 100}%`, background: 'linear-gradient(90deg,var(--indigo),var(--emerald))', borderRadius: 3 }} />
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--emerald)', minWidth: 36 }}>{Math.round(a.approval_rate * 100)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
