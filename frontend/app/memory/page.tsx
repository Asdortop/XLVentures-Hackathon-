'use client'
import { useState, useEffect, useRef } from 'react'
import { useApp } from '../context'

interface GraphNode {
  id: string
  label: string
  decisions: number
  approved: number
  rejected: number
  intents: string[]
  success_rate: number
}
interface GraphEdge { source: string; target: string; weight: number; relationship: string }
interface SqlPattern {
  id: number; issue_type: string; issue_text: string; resolution: string
  success_count: number; failure_count: number; success_rate: number; last_used: string | null
}
interface SemanticMemory {
  id: string; document: string; issue_type: string; resolution: string
  entity_name: string; severity: string; approved: boolean | null
  success_count: number; is_correction: boolean
}
interface Decision {
  nba_id: number; entity_name: string; intent: string; severity: string
  status: string; top_action: string; confidence: number; created_at: string; rejection_reason: string | null
}
interface MemoryData {
  domain_id: number; domain_slug: string
  sql_patterns: SqlPattern[]; semantic_memories: SemanticMemory[]
  semantic_count: number; graph_nodes: GraphNode[]; graph_edges: GraphEdge[]
  decision_timeline: Decision[]
  summary: { sql_pattern_count: number; semantic_memory_count: number; entity_count: number; edge_count: number; total_decisions: number }
}

type Tab = 'overview' | 'semantic' | 'graph' | 'timeline'

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--red)', high: 'var(--amber)', medium: 'var(--indigo)', low: 'var(--emerald)'
}

// Simple force-layout canvas graph
function GraphCanvas({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current || nodes.length === 0) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')!
    const W = canvas.width, H = canvas.height

    // Simple circular layout
    const positions: Record<string, { x: number; y: number }> = {}
    const cx = W / 2, cy = H / 2
    const r = Math.min(W, H) * 0.35

    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI - Math.PI / 2
      positions[n.id] = {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      }
    })

    // Background
    ctx.fillStyle = '#0d1117'
    ctx.fillRect(0, 0, W, H)

    // Draw edges
    edges.forEach(e => {
      const from = positions[e.source], to = positions[e.target]
      if (!from || !to) return
      ctx.beginPath()
      ctx.moveTo(from.x, from.y)
      ctx.lineTo(to.x, to.y)
      ctx.strokeStyle = 'rgba(99,102,241,0.25)'
      ctx.lineWidth = Math.min(e.weight, 3)
      ctx.stroke()
    })

    // Draw nodes
    nodes.forEach(n => {
      const pos = positions[n.id]
      if (!pos) return
      const nodeR = 8 + Math.min(n.decisions * 2, 16)
      const color = n.success_rate >= 0.7 ? '#10b981' : n.success_rate >= 0.4 ? '#f59e0b' : '#ef4444'

      // Glow
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, nodeR + 4, 0, 2 * Math.PI)
      ctx.fillStyle = color + '20'
      ctx.fill()

      // Node circle
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, nodeR, 0, 2 * Math.PI)
      ctx.fillStyle = color + 'cc'
      ctx.fill()
      ctx.strokeStyle = color
      ctx.lineWidth = 1.5
      ctx.stroke()

      // Label
      ctx.fillStyle = '#e2e8f0'
      ctx.font = '11px Inter, sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      const maxLen = 10
      const label = n.label.length > maxLen ? n.label.slice(0, maxLen) + '…' : n.label
      ctx.fillText(label, pos.x, pos.y + nodeR + 12)

      // Decision count badge
      if (n.decisions > 0) {
        ctx.fillStyle = '#6366f1'
        ctx.beginPath()
        ctx.arc(pos.x + nodeR - 2, pos.y - nodeR + 2, 8, 0, 2 * Math.PI)
        ctx.fill()
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 9px Inter, sans-serif'
        ctx.fillText(String(n.decisions), pos.x + nodeR - 2, pos.y - nodeR + 2)
      }
    })
  }, [nodes, edges])

  if (nodes.length === 0) {
    return (
      <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px dashed var(--border)', borderRadius: 'var(--radius-md)', color: 'var(--text-muted)', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontSize: 32, opacity: 0.3 }}>⬡</div>
        <div style={{ fontSize: 13 }}>No entity graph yet — submit interactions to build it</div>
      </div>
    )
  }

  return (
    <div style={{ position: 'relative' }}>
      <canvas ref={canvasRef} width={680} height={340}
        style={{ width: '100%', height: 340, borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }} />
      <div style={{ position: 'absolute', top: 10, right: 10, display: 'flex', flexDirection: 'column', gap: 4, fontSize: 10, color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }} /> High success</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b' }} /> Medium</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444' }} /> Low success</div>
        <div style={{ marginTop: 4, color: 'var(--text-muted)' }}>Node size = decisions</div>
      </div>
    </div>
  )
}

export default function MemoryPage() {
  const { domain } = useApp()
  const [data, setData] = useState<MemoryData | null>(null)
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState<Tab>('overview')

  useEffect(() => {
    if (!domain) return
    setLoading(true)
    fetch(`/api/memory/${domain.id}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [domain])

  const tabs: Array<{ id: Tab; label: string; icon: string; count?: number }> = [
    { id: 'overview', label: 'Overview', icon: '◎' },
    { id: 'semantic', label: 'Semantic Memory', icon: '🧠', count: data?.semantic_count },
    { id: 'graph', label: 'Entity Graph', icon: '⬡', count: data?.summary.entity_count },
    { id: 'timeline', label: 'Decision Timeline', icon: '◈', count: data?.summary.total_decisions },
  ]

  return (
    <div style={{ maxWidth: 1100 }}>
      <div className="page-header">
        <div className="page-title">Memory Explorer</div>
        <div className="page-subtitle">
          What the system has learned — semantic memories, entity relationships, and decision patterns
        </div>
      </div>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 40, color: 'var(--text-muted)' }}>
          <div className="spinner" style={{ width: 20, height: 20 }} /> Loading memory data...
        </div>
      )}

      {!loading && !data && (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>Select a domain to explore its memory</div>
      )}

      {data && !loading && (
        <>
          {/* Summary stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
            {[
              { label: 'SQL Patterns', value: data.summary.sql_pattern_count, icon: '◎', color: 'var(--indigo)' },
              { label: 'Semantic Memories', value: data.summary.semantic_memory_count, icon: '🧠', color: 'var(--emerald)' },
              { label: 'Known Entities', value: data.summary.entity_count, icon: '⬡', color: 'var(--amber)' },
              { label: 'Past Decisions', value: data.summary.total_decisions, icon: '◈', color: 'var(--indigo-light)' },
            ].map(s => (
              <div key={s.label} className="card" style={{ padding: '16px 20px', textAlign: 'center' }}>
                <div style={{ fontSize: 22, marginBottom: 4, color: s.color }}>{s.icon}</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
            {tabs.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                style={{
                  background: 'none', border: 'none', padding: '8px 16px', cursor: 'pointer',
                  color: tab === t.id ? 'var(--indigo-light)' : 'var(--text-muted)',
                  borderBottom: tab === t.id ? '2px solid var(--indigo)' : '2px solid transparent',
                  fontSize: 13, fontWeight: tab === t.id ? 600 : 400,
                  display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.15s'
                }}>
                {t.icon} {t.label}
                {t.count !== undefined && t.count > 0 && (
                  <span style={{ background: 'var(--indigo-dim)', color: 'var(--indigo-light)', borderRadius: 10, padding: '1px 6px', fontSize: 10 }}>
                    {t.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Overview tab */}
          {tab === 'overview' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              {/* SQL Patterns */}
              <div className="card">
                <div className="section-title" style={{ marginBottom: 14 }}>◎ Learned SQL Patterns</div>
                {data.sql_patterns.length === 0 && (
                  <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '20px 0' }}>
                    No patterns yet — approve/reject NBAs to train the system
                  </div>
                )}
                {data.sql_patterns.map(p => (
                  <div key={p.id} style={{ padding: '10px 0', borderBottom: '1px solid var(--border-muted)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--indigo-light)' }}>{p.issue_type}</span>
                      <span style={{ fontSize: 11, color: p.success_rate >= 0.7 ? 'var(--emerald)' : 'var(--amber)' }}>
                        {Math.round(p.success_rate * 100)}% success · {p.success_count}×
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>{p.issue_text}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontStyle: 'italic' }}>→ {p.resolution}</div>
                  </div>
                ))}
              </div>

              {/* Mini graph preview */}
              <div className="card">
                <div className="section-title" style={{ marginBottom: 14 }}>⬡ Entity Knowledge Graph</div>
                <GraphCanvas nodes={data.graph_nodes} edges={data.graph_edges} />
                {data.graph_nodes.length > 0 && (
                  <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {data.graph_nodes.map(n => (
                      <span key={n.id} style={{
                        padding: '3px 8px', borderRadius: 12, fontSize: 11,
                        background: `rgba(99,102,241,${Math.min(0.1 + n.decisions * 0.1, 0.4)})`,
                        border: '1px solid rgba(99,102,241,0.3)', color: 'var(--indigo-light)'
                      }}>
                        {n.label} ({n.decisions}d)
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Semantic Memory tab */}
          {tab === 'semantic' && (
            <div>
              {data.semantic_memories.length === 0 && (
                <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.3 }}>🧠</div>
                  <div>No semantic memories stored yet</div>
                  <div style={{ fontSize: 12, marginTop: 8 }}>Approve or reject NBAs to populate the vector memory</div>
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {data.semantic_memories.map((m, i) => (
                  <div key={m.id} className="card" style={{ padding: '14px 18px', borderLeft: `3px solid ${m.is_correction ? 'var(--amber)' : m.approved === false ? 'var(--red)' : 'var(--emerald)'}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--indigo-light)', background: 'var(--indigo-dim)', padding: '2px 8px', borderRadius: 10 }}>
                          {m.issue_type || 'general'}
                        </span>
                        {m.entity_name && (
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>⬡ {m.entity_name}</span>
                        )}
                        {m.severity && (
                          <span style={{ fontSize: 10, color: SEV_COLOR[m.severity] || 'var(--text-muted)' }}>● {m.severity}</span>
                        )}
                        {m.is_correction && (
                          <span style={{ fontSize: 10, color: 'var(--amber)', background: 'rgba(245,158,11,0.1)', padding: '2px 6px', borderRadius: 8 }}>
                            correction
                          </span>
                        )}
                      </div>
                      <span style={{ fontSize: 11, color: m.approved === false ? 'var(--red)' : 'var(--emerald)', fontWeight: 600 }}>
                        {m.approved === false ? '✕ rejected' : '✓ approved'}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, lineHeight: 1.5 }}>
                      "{m.document}"
                    </div>
                    {m.resolution && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        → Resolution: {m.resolution}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Entity Graph tab */}
          {tab === 'graph' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div className="card">
                <div className="section-title" style={{ marginBottom: 14 }}>⬡ Entity Relationship Graph</div>
                <GraphCanvas nodes={data.graph_nodes} edges={data.graph_edges} />
              </div>

              {data.graph_nodes.length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
                  {data.graph_nodes.map(n => (
                    <div key={n.id} className="card" style={{ padding: '12px 16px' }}>
                      <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 14 }}>⬡ {n.label}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, fontSize: 11, color: 'var(--text-muted)' }}>
                        <span>Decisions</span><span style={{ color: 'var(--text-secondary)', textAlign: 'right' }}>{n.decisions}</span>
                        <span>Approved</span><span style={{ color: 'var(--emerald)', textAlign: 'right' }}>{n.approved}</span>
                        <span>Rejected</span><span style={{ color: 'var(--red)', textAlign: 'right' }}>{n.rejected}</span>
                        <span>Success rate</span><span style={{ color: n.success_rate >= 0.7 ? 'var(--emerald)' : 'var(--amber)', textAlign: 'right', fontWeight: 600 }}>{Math.round(n.success_rate * 100)}%</span>
                      </div>
                      {n.intents.length > 0 && (
                        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {n.intents.slice(0, 3).map(intent => (
                            <span key={intent} style={{ fontSize: 10, padding: '1px 6px', borderRadius: 8, background: 'var(--indigo-dim)', color: 'var(--indigo-light)' }}>
                              {intent}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Decision Timeline tab */}
          {tab === 'timeline' && (
            <div>
              {data.decision_timeline.length === 0 && (
                <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.3 }}>◈</div>
                  <div>No completed decisions yet — approve or reject NBAs to build history</div>
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {data.decision_timeline.map((d, i) => (
                  <div key={d.nba_id} className="card" style={{
                    padding: '12px 18px', display: 'flex', gap: 16, alignItems: 'flex-start',
                    borderLeft: `3px solid ${d.status === 'approved' ? 'var(--emerald)' : 'var(--red)'}`
                  }}>
                    <div style={{ width: 44, height: 44, borderRadius: '50%', background: d.status === 'approved' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>
                      {d.status === 'approved' ? '✓' : '✕'}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 14 }}>⬡ {d.entity_name || 'Unknown'}</span>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          {new Date(d.created_at).toLocaleDateString()} {new Date(d.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
                        → {d.top_action}
                      </div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {d.intent && <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 8, background: 'var(--indigo-dim)', color: 'var(--indigo-light)' }}>{d.intent}</span>}
                        {d.severity && <span style={{ fontSize: 10, color: SEV_COLOR[d.severity] || 'var(--text-muted)' }}>● {d.severity}</span>}
                        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{Math.round(d.confidence * 100)}% confidence</span>
                      </div>
                      {d.rejection_reason && (
                        <div style={{ marginTop: 6, fontSize: 11, color: 'var(--red)', fontStyle: 'italic', background: 'rgba(239,68,68,0.05)', padding: '4px 8px', borderRadius: 4 }}>
                          Reason: {d.rejection_reason}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
