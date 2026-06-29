'use client'
import { useEffect, useState } from 'react'
import { useApp } from '../context'

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
  const trend = data?.confidence_trend ?? {}
  const trendDelta = trend.delta ?? 0
  const trendUp = trend.improving

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Outcomes Dashboard</div>
        <div className="page-subtitle">Measurable business impact of {domain?.label} — approval rates, memory growth, value generated</div>
      </div>

      {/* ── Tier 1 KPIs ─────────────────────────────────────────────────── */}
      <div className="grid-4" style={{ marginBottom: 28 }}>
        <div className="stat-card">
          <div className="stat-value">{data?.total_nbas ?? 0}</div>
          <div className="stat-label">Decisions Supported</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>{data?.pending ?? 0} pending review</div>
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
            {(data?.pattern_count ?? 0) + (data?.semantic_memory_count ?? 0)}
          </div>
          <div className="stat-label">Memory Items</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>
            {data?.pattern_count ?? 0} SQL · {data?.semantic_memory_count ?? 0} semantic
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ background: 'linear-gradient(135deg,var(--amber),var(--red))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {data?.value_metric?.total > 0 ? `$${(data.value_metric.total / 1000).toFixed(0)}K` : data?.approved ?? 0}
          </div>
          <div className="stat-label">{data?.value_metric?.label || 'Approved Decisions'}</div>
        </div>
      </div>

      {/* ── New Business Metrics Row ─────────────────────────────────────── */}
      <div className="grid-4" style={{ marginBottom: 28 }}>
        {/* Time to Decision */}
        <div className="card" style={{ padding: '16px 18px', textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>⏱ Avg Time-to-Decision</div>
          <div style={{ fontSize: 26, fontWeight: 800 }}>
            {data?.avg_time_to_decision_minutes > 0 ? `${data.avg_time_to_decision_minutes}m` : '—'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>creation → approve/reject</div>
        </div>

        {/* Value Awaiting */}
        <div className="card" style={{ padding: '16px 18px', textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>💰 Value Awaiting Action</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--amber)' }}>
            {data?.value_awaiting > 0 ? `$${(data.value_awaiting / 1000).toFixed(0)}K` : '$0'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>{data?.pending ?? 0} pending × ${data?.value_metric?.per_approved_nba?.toLocaleString() ?? 0}</div>
        </div>

        {/* Confidence Trend */}
        <div className="card" style={{ padding: '16px 18px', textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>📈 Memory Accuracy Trend</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: trendDelta > 0 ? 'var(--emerald)' : trendDelta < 0 ? 'var(--red)' : 'var(--text-secondary)' }}>
            {trendDelta > 0 ? '+' : ''}{trendDelta}%
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
            {trend.first_avg}% → {trend.last_avg}% confidence
          </div>
        </div>

        {/* Semantic Memory */}
        <div className="card" style={{ padding: '16px 18px', textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>🧠 Semantic Memories</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--indigo-light)' }}>
            {data?.semantic_memory_count ?? 0}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>vector embeddings stored</div>
        </div>
      </div>

      {/* Confidence Trend Bar — the "proof of learning" visual */}
      {trend.first_avg > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="section-title">📈 Confidence Improving Over Time</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: 'var(--text-secondary)' }}>Early decisions (first 5 approved)</span>
                <span style={{ fontWeight: 700 }}>{trend.first_avg}%</span>
              </div>
              <div style={{ height: 8, background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${trend.first_avg}%`, background: 'var(--indigo)', borderRadius: 4 }} />
              </div>
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: 'var(--text-secondary)' }}>Recent decisions (last 5 approved)</span>
                <span style={{ fontWeight: 700, color: trendUp ? 'var(--emerald)' : 'var(--red)' }}>{trend.last_avg}%</span>
              </div>
              <div style={{ height: 8, background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${trend.last_avg}%`, background: `linear-gradient(90deg,var(--indigo),${trendUp ? 'var(--emerald)' : 'var(--red)'})`, borderRadius: 4, transition: 'width 1s ease' }} />
              </div>
            </div>
          </div>
          <div style={{ marginTop: 12, padding: '8px 12px', background: trendUp ? 'rgba(16,185,129,0.1)' : 'rgba(99,102,241,0.08)', border: `1px solid ${trendUp ? 'rgba(16,185,129,0.3)' : 'rgba(99,102,241,0.2)'}`, borderRadius: 'var(--radius-sm)', fontSize: 12, color: trendUp ? 'var(--emerald)' : 'var(--text-secondary)' }}>
            {trendUp
              ? `✓ System is learning — confidence improved by +${trendDelta}% since first approvals`
              : 'Approve more recommendations to build memory and improve confidence'}
          </div>
        </div>
      )}

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
              <div style={{ fontSize: 28, fontWeight: 800 }}>{approvalPct}%</div>
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

        {/* Memory Patterns */}
        <div className="card">
          <div className="section-title">◈ Top Memory Patterns</div>
          {!data?.top_patterns?.length ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No patterns yet — approve some NBAs to build memory.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {data.top_patterns.map((p: any, i: number) => (
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

      {/* Top Performing Actions */}
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
