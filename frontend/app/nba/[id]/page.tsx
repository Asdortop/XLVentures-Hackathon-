'use client'
import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'

const AGENTS = ['Planner', 'Context', 'Dependency', 'Risk', 'Recommender']
const AGENT_ICONS = { Planner: '✦', Context: '◈', Dependency: '⬡', Risk: '◎', Recommender: '★' }

const EVIDENCE_LABELS: Record<string, string> = {
  playbook: '📘 Playbook',
  similar_case: '✓ Past Case',
  crm: '◈ CRM Record',
  graph_path: '⬡ Dependency',
  risk_signal: '◎ Risk Signal',
  interaction: '✦ Interaction',
}

export default function NBADetail() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [nba, setNba] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeStep, setActiveStep] = useState<string | null>(null)
  const [rejecting, setRejecting] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [toast, setToast] = useState('')

  useEffect(() => {
    fetch(`/api/nba/detail/${id}`).then(r => r.json()).then(d => {
      setNba(d)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [id])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const handleApprove = async () => {
    setActionLoading(true)
    try {
      await fetch(`/api/nba/detail/${id}/approve`, { method: 'POST' })
      showToast('✓ NBA approved — memory updated')
      setNba((n: any) => ({ ...n, hitl_status: 'approved' }))
    } catch { showToast('Error approving') }
    setActionLoading(false)
  }

  const handleReject = async () => {
    setActionLoading(true)
    try {
      await fetch(`/api/nba/detail/${id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: rejectReason }),
      })
      showToast('Rejected — memory updated')
      setNba((n: any) => ({ ...n, hitl_status: 'rejected' }))
      setRejecting(false)
    } catch { showToast('Error rejecting') }
    setActionLoading(false)
  }

  const getAgentLog = (agentName: string) => {
    if (!nba?.agent_log) return []
    const entry = nba.agent_log.find((l: any) => l.agent === agentName)
    return entry?.steps || []
  }

  if (loading) return <div className="loading-overlay"><div className="spinner" /><span>Loading NBA...</span></div>
  if (!nba) return <div className="empty-state"><div className="empty-title">NBA not found</div></div>

  return (
    <div style={{ maxWidth: 900 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Link href="/nba"><span style={{ fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer' }}>← Back to Inbox</span></Link>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: 12 }}>
          <div>
            <div className="page-title">{nba.entity_name}</div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
              <span className={`badge badge-${nba.severity}`}>{nba.severity}</span>
              <span className={`badge badge-${nba.hitl_status}`}>{nba.hitl_status}</span>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Intent: <strong style={{ color: 'var(--indigo-light)' }}>{nba.matched_intent}</strong></span>
              {nba.blast_radius && <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Blast: {nba.blast_radius}</span>}
            </div>
          </div>
          {nba.hitl_status === 'pending' && (
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-success" onClick={handleApprove} disabled={actionLoading}>
                {actionLoading ? <span className="spinner" /> : '✓'} Approve All
              </button>
              <button className="btn btn-danger" onClick={() => setRejecting(!rejecting)} disabled={actionLoading}>
                ✕ Reject
              </button>
            </div>
          )}
        </div>

        {rejecting && (
          <div className="card-sm" style={{ marginTop: 12, border: '1px solid rgba(239,68,68,0.3)' }}>
            <input className="form-input" placeholder="Reason for rejection (optional)" value={rejectReason} onChange={e => setRejectReason(e.target.value)} style={{ marginBottom: 10 }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-danger btn-sm" onClick={handleReject}>Confirm Reject</button>
              <button className="btn btn-ghost btn-sm" onClick={() => setRejecting(false)}>Cancel</button>
            </div>
          </div>
        )}
      </div>

      {/* Agent Stepper */}
      <div style={{ marginBottom: 24 }}>
        <div className="section-title">Agent Pipeline Trace</div>
        <div className="agent-stepper">
          {AGENTS.map((agent, i) => (
            <div key={agent} className="agent-step">
              <div
                className={`step-node ${nba.agent_log?.some((l: any) => l.agent === agent) ? 'completed' : ''}`}
                onClick={() => setActiveStep(activeStep === agent ? null : agent)}
              >
                <span className="step-icon">{AGENT_ICONS[agent as keyof typeof AGENT_ICONS]}</span>
                <span>{agent}</span>
              </div>
              {i < AGENTS.length - 1 && <div className={`step-connector ${nba.agent_log?.some((l: any) => l.agent === agent) ? 'completed' : ''}`} />}
            </div>
          ))}
        </div>
        {activeStep && (
          <div className="step-log">
            {getAgentLog(activeStep).map((step: string, i: number) => (
              <div key={i} className="step-log-entry">{step}</div>
            ))}
            {getAgentLog(activeStep).length === 0 && <div style={{ color: 'var(--text-muted)' }}>No logs for this agent.</div>}
          </div>
        )}
      </div>

      {/* Actions */}
      <div>
        <div className="section-title">★ Ranked Recommendations ({nba.actions?.length})</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {nba.actions?.map((action: any) => (
            <div key={action.id} className="card">
              <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start', marginBottom: 14 }}>
                <div className="action-rank">#{action.rank}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>{action.action}</div>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Owner: <strong>{action.owner}</strong></span>
                    <span className={`badge badge-${action.priority}`}>{action.priority}</span>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>~{action.estimated_hours}h</span>
                  </div>
                </div>
              </div>

              {/* Confidence Bar */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                  <span>Confidence</span>
                  <span style={{ color: 'var(--indigo-light)', fontWeight: 700 }}>{Math.round(action.confidence * 100)}%</span>
                </div>
                <div className="confidence-bar-track">
                  <div className="confidence-bar-fill" style={{ width: `${action.confidence * 100}%` }} />
                </div>
              </div>

              {/* Evidence */}
              {action.evidence?.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>Supporting Evidence</div>
                  <div className="evidence-panel">
                    {action.evidence.map((ev: any, i: number) => (
                      <div key={i} className={`evidence-card ${ev.type}`}>
                        <div className="evidence-source">{EVIDENCE_LABELS[ev.type] || ev.type} · {ev.source}</div>
                        <div className="evidence-content">{ev.content}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {toast && <div className="toast" style={{ color: toast.startsWith('✓') ? 'var(--emerald)' : 'var(--text-primary)' }}>{toast}</div>}
    </div>
  )
}
