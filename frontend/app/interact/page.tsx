'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useApp } from '../layout'

const AGENT_META: Record<string, { icon: string; label: string; color: string; desc: string }> = {
  planner:     { icon: '✦', label: 'Planner',     color: '#818cf8', desc: 'Classifying intent & context' },
  context:     { icon: '◈', label: 'Context',     color: '#06b6d4', desc: 'Searching memory & past cases' },
  dependency:  { icon: '⬡', label: 'Dependency',  color: '#a855f7', desc: 'Mapping entity relationships' },
  risk:        { icon: '◎', label: 'Risk',         color: '#f59e0b', desc: 'Evaluating severity & urgency' },
  recommender: { icon: '★', label: 'Recommender', color: '#10b981', desc: 'Ranking next best actions' },
  critic:      { icon: '⚑', label: 'Critic',      color: '#c084fc', desc: 'Reflecting on quality' },
}
const AGENT_ORDER = ['planner', 'context', 'dependency', 'risk', 'recommender', 'critic']

const SEV_COLOR: Record<string, string> = {
  critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#10b981'
}

interface AgentEvent {
  agent: string; icon: string; summary: string; steps: string[]
  severity?: string; matched_intent?: string
}

type Phase = 'idle' | 'processing' | 'results'

export default function InteractPage() {
  const { domain } = useApp()
  const router = useRouter()
  const [entityName, setEntityName] = useState('')
  const [text, setText] = useState('')
  const [scenarios, setScenarios] = useState<any[]>([])
  const [placeholder, setPlaceholder] = useState('Paste customer interaction here...')
  const [error, setError] = useState('')

  // Phase & streaming state
  const [phase, setPhase] = useState<Phase>('idle')
  const [completedAgents, setCompletedAgents] = useState<AgentEvent[]>([])
  const [currentAgent, setCurrentAgent] = useState<string | null>(null)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  // Results state
  const [nbaData, setNbaData] = useState<any>(null)
  const [nbaId, setNbaId] = useState<number | null>(null)
  const [visibleCards, setVisibleCards] = useState<number>(0)

  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!domain) return
    fetch(`/api/domains/${domain.id}/demo`).then(r => r.json()).then(d => {
      setEntityName(d.entity_name || '')
      setText(d.text || '')
      setPlaceholder(d.placeholder || 'Paste customer interaction here...')
      setScenarios(d.sample_scenarios || [])
    }).catch(() => {})
  }, [domain])

  // Stagger-animate recommendation cards
  useEffect(() => {
    if (phase !== 'results' || !nbaData) return
    const actions = nbaData.actions || []
    let i = 0
    const timer = setInterval(() => {
      i++
      setVisibleCards(i)
      if (i >= actions.length) clearInterval(timer)
    }, 160)
    return () => clearInterval(timer)
  }, [phase, nbaData])

  // Auto-scroll during processing
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [completedAgents.length, phase])

  const handleScenario = (s: any) => { setEntityName(s.entity_name); setText(s.text) }

  const handleSubmit = async () => {
    if (!domain || !text.trim() || !entityName.trim()) return
    setPhase('processing')
    setError('')
    setCompletedAgents([])
    setCurrentAgent(null)
    setNbaData(null)
    setNbaId(null)
    setVisibleCards(0)

    try {
      const response = await fetch('/api/interactions/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain_id: domain.id, entity_name: entityName, text }),
      })
      if (!response.ok) throw new Error(`Server error: ${response.status}`)
      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'agent_done') {
              setCurrentAgent(event.agent)
              setCompletedAgents(prev => [...prev, {
                agent: event.agent, icon: event.icon, summary: event.summary,
                steps: event.steps || [], severity: event.severity, matched_intent: event.matched_intent,
              }])
            } else if (event.type === 'pipeline_complete') {
              setCurrentAgent(null)
              const id = event.nba_id
              setNbaId(id)
              // Fetch full NBA data then switch to results phase
              const nbaRes = await fetch(`/api/nba/detail/${id}`)
              const nba = await nbaRes.json()
              setNbaData(nba)
              // Small pause to let "complete" state render, then reveal results
              setTimeout(() => setPhase('results'), 600)
              return
            } else if (event.type === 'pipeline_error') {
              throw new Error(event.error || 'Pipeline failed')
            }
          } catch (_) {}
        }
      }
    } catch (e: any) {
      setError(e.message || 'Submission failed')
      setPhase('idle')
    }
  }

  const handleReset = () => {
    setPhase('idle')
    setCompletedAgents([])
    setNbaData(null)
    setNbaId(null)
    setVisibleCards(0)
    setExpandedAgent(null)
  }

  const allDone = completedAgents.length === AGENT_ORDER.length
  const sevColor = nbaData?.severity ? (SEV_COLOR[nbaData.severity] || '#6366f1') : '#6366f1'

  return (
    <div style={{ maxWidth: 860 }}>
      <div className="page-header">
        <div className="page-title">Submit Interaction</div>
        <div className="page-subtitle">Paste a customer signal — watch 6 agents reason live, then review ranked Next Best Actions</div>
      </div>

      {/* ── IDLE: Input form ─────────────────────────────────────── */}
      {phase === 'idle' && (
        <div className="fade-in">
          {/* Agent pipeline pill */}
          <div className="card" style={{ marginBottom: 20, padding: '14px 20px', background: 'linear-gradient(135deg,rgba(99,102,241,0.06),rgba(168,85,247,0.06))' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
              <span style={{ color: 'var(--text-muted)' }}>Pipeline:</span>
              {AGENT_ORDER.map((a, i, arr) => {
                const m = AGENT_META[a]
                return (
                  <span key={a} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ color: m.color, fontWeight: 600 }}>{m.icon} {m.label}</span>
                    {i < arr.length - 1 && <span style={{ color: 'var(--text-muted)' }}>→</span>}
                  </span>
                )
              })}
            </div>
          </div>

          <div className="card">
            <div className="form-group">
              <label className="form-label">{domain?.entity_label || 'Entity'} Name *</label>
              <input className="form-input" value={entityName} onChange={e => setEntityName(e.target.value)} placeholder="e.g. Acme Corp, GlobalBank CFO Search..." />
            </div>
            <div className="form-group">
              <label className="form-label">Interaction Text *</label>
              <textarea className="form-textarea" style={{ minHeight: 160 }} value={text} onChange={e => setText(e.target.value)} placeholder={placeholder} />
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                Meeting notes, CRM updates, emails — any signal about this {domain?.entity_label?.toLowerCase() || 'entity'}
              </div>
            </div>

            {scenarios.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Or try a sample:</div>
                <div className="scenario-chips">
                  {scenarios.map((s, i) => (
                    <button key={i} className="chip" onClick={() => handleScenario(s)}>{s.label}</button>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-md)', fontSize: 13, color: 'var(--red)', marginBottom: 16 }}>
                {error}
              </div>
            )}

            <button className="btn btn-primary btn-lg" onClick={handleSubmit}
              disabled={!text.trim() || !entityName.trim() || !domain}
              style={{ width: '100%', justifyContent: 'center' }}>
              ✦ Analyze &amp; Generate Recommendations
            </button>
          </div>
        </div>
      )}

      {/* ── PROCESSING: Live agent pipeline ──────────────────────── */}
      {(phase === 'processing' || (phase === 'results' && completedAgents.length > 0)) && (
        <div style={{ marginBottom: phase === 'results' ? 32 : 0 }}>
          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20, padding: '16px 20px',
            background: 'linear-gradient(135deg,rgba(99,102,241,0.08),rgba(168,85,247,0.06))',
            borderRadius: 'var(--radius-lg)', border: '1px solid rgba(99,102,241,0.2)'
          }}>
            {phase === 'processing'
              ? <div className="spinner" style={{ width: 22, height: 22, flexShrink: 0 }} />
              : <div className="complete-pop" style={{ fontSize: 22, color: 'var(--emerald)', flexShrink: 0 }}>✓</div>
            }
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 15 }}>
                {phase === 'processing' ? 'Agent Pipeline Running' : 'Analysis Complete'}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                {entityName} · {domain?.label} · {completedAgents.length}/{AGENT_ORDER.length} agents
              </div>
            </div>
            {/* Progress bar */}
            <div style={{ width: 120, height: 4, background: 'rgba(99,102,241,0.15)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 4,
                background: 'linear-gradient(90deg, var(--indigo), var(--purple))',
                width: `${(completedAgents.length / AGENT_ORDER.length) * 100}%`,
                transition: 'width 0.4s ease',
              }} />
            </div>
          </div>

          {/* Agent nodes */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
            {AGENT_ORDER.map((agentKey) => {
              const meta = AGENT_META[agentKey]
              const done = completedAgents.find(a => a.agent === agentKey)
              const isActive = currentAgent === agentKey && phase === 'processing'
              const isPending = !done && !isActive

              return (
                <div
                  key={agentKey}
                  onClick={() => done && setExpandedAgent(expandedAgent === agentKey ? null : agentKey)}
                  className={isActive ? 'agent-node-active' : ''}
                  style={{
                    padding: '12px 14px', borderRadius: 'var(--radius-md)', cursor: done ? 'pointer' : 'default',
                    background: done ? `${meta.color}14` : isActive ? 'rgba(255,255,255,0.04)' : 'var(--bg-card)',
                    border: `1px solid ${done ? meta.color + '44' : isActive ? meta.color + '66' : 'var(--border)'}`,
                    transition: 'all 0.3s ease',
                    position: 'relative', overflow: 'hidden',
                  }}
                >
                  {/* Shimmer on active */}
                  {isActive && (
                    <div className="shimmer-top" style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2 }} />
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div
                      className={isActive ? 'agent-icon-active' : ''}
                      style={{
                        width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                        background: done ? meta.color : isActive ? meta.color + '33' : 'var(--bg-elevated)',
                        border: `1.5px solid ${done ? 'transparent' : meta.color + '66'}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 14, fontWeight: 700,
                        color: done ? '#fff' : isPending ? 'var(--text-muted)' : meta.color,
                        transition: 'all 0.3s',
                      }}
                    >
                      {isActive
                        ? <div className="spinner" style={{ width: 14, height: 14, borderColor: meta.color, borderTopColor: 'transparent' }} />
                        : done ? '✓' : meta.icon
                      }
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: done ? 'var(--text-primary)' : isActive ? meta.color : 'var(--text-muted)' }}>
                        {meta.icon} {meta.label}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {done ? done.summary : isActive ? meta.desc : meta.desc}
                      </div>
                    </div>
                    {done && (
                      <span style={{ fontSize: 9, color: 'var(--text-muted)', flexShrink: 0 }}>
                        {expandedAgent === agentKey ? '▲' : '▼'}
                      </span>
                    )}
                  </div>

                  {/* Expanded steps */}
                  {expandedAgent === agentKey && done && done.steps.length > 0 && (
                    <div className="fade-in" style={{ marginTop: 10, padding: '8px 10px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', borderLeft: `2px solid ${meta.color}` }}>
                      {done.steps.map((step, i) => (
                        <div key={i} style={{ fontSize: 10, color: 'var(--text-secondary)', padding: '2px 0', fontFamily: 'monospace', lineHeight: 1.5 }}>
                          {step}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Data flow connector */}
          {phase === 'processing' && !allDone && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 11, marginBottom: 8 }}>
              <svg width="100%" height="6" style={{ display: 'block' }}>
                <line x1="0" y1="3" x2="100%" y2="3"
                  stroke="url(#flowGrad)" strokeWidth="2" strokeDasharray="8 4"
                  style={{ animation: 'dataFlow 1.5s linear infinite' }} />
                <defs>
                  <linearGradient id="flowGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="transparent" />
                    <stop offset="50%" stopColor="#6366f1" />
                    <stop offset="100%" stopColor="transparent" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
          )}

          {/* All done banner (processing phase) */}
          {allDone && phase === 'processing' && (
            <div className="complete-pop" style={{
              padding: '12px 16px', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)',
              borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <span style={{ color: 'var(--emerald)', fontSize: 18 }}>✓</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--emerald)' }}>All 6 agents complete — loading recommendations...</span>
            </div>
          )}
        </div>
      )}

      {/* ── RESULTS: Animated recommendations ────────────────────── */}
      {phase === 'results' && nbaData && (
        <div className="fade-in">
          {/* Severity + meta header */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: 20, padding: '14px 20px',
            background: `${sevColor}12`, border: `1px solid ${sevColor}44`,
            borderRadius: 'var(--radius-lg)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{
                width: 38, height: 38, borderRadius: '50%',
                background: `${sevColor}22`, border: `2px solid ${sevColor}66`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 16, color: sevColor,
              }}>◎</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>⬡ {nbaData.entity_name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 1 }}>
                  {nbaData.matched_intent && <span style={{ marginRight: 8 }}>◈ {nbaData.matched_intent?.replace(/_/g, ' ')}</span>}
                  {nbaData.severity && <span style={{ color: sevColor, fontWeight: 600 }}>● {nbaData.severity?.toUpperCase()}</span>}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-ghost btn-sm" onClick={handleReset}>← New Interaction</button>
              {nbaId && (
                <button className="btn btn-primary btn-sm" onClick={() => router.push(`/nba/${nbaId}`)}>
                  Full Analysis →
                </button>
              )}
            </div>
          </div>

          {/* Heading */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
              ★ Ranked Next Best Actions · {nbaData.actions?.length || 0} recommendations
            </div>
          </div>

          {/* Recommendation cards with stagger animation */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {(nbaData.actions || []).map((action: any, idx: number) => {
              if (idx >= visibleCards) return null
              const isTop = idx === 0
              const conf = Math.round((action.confidence || 0) * 100)

              return (
                <div
                  key={action.id}
                  className="rec-card-enter"
                  style={{
                    animationDelay: `${idx * 0.06}s`,
                    position: 'relative', overflow: 'hidden',
                    background: isTop
                      ? 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(168,85,247,0.08))'
                      : 'var(--bg-card)',
                    border: `1px solid ${isTop ? 'rgba(99,102,241,0.4)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-lg)', padding: '16px 20px',
                    transition: 'border-color 0.2s, box-shadow 0.2s',
                    boxShadow: isTop ? '0 4px 24px rgba(99,102,241,0.12)' : 'none',
                  }}
                >
                  {/* Top recommendation shimmer line */}
                  {isTop && (
                    <div className="shimmer-top" style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0' }} />
                  )}

                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                    {/* Rank badge */}
                    <div style={{
                      width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
                      background: isTop ? 'var(--indigo)' : 'var(--bg-elevated)',
                      border: `1.5px solid ${isTop ? 'rgba(99,102,241,0.6)' : 'var(--border)'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: isTop ? 13 : 11, fontWeight: 800, color: isTop ? '#fff' : 'var(--text-muted)',
                    }}>
                      {isTop ? '★' : `#${idx + 1}`}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      {isTop && (
                        <div style={{ fontSize: 10, color: 'var(--indigo-light)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
                          ✦ Top Recommendation
                        </div>
                      )}
                      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4, color: isTop ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                        {action.action}
                      </div>

                      {/* Confidence bar */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                        <div style={{ flex: 1, height: 4, background: 'rgba(99,102,241,0.15)', borderRadius: 4, overflow: 'hidden' }}>
                          <div
                            className="conf-bar-fill"
                            style={{
                              height: '100%', borderRadius: 4, width: `${conf}%`,
                              background: conf >= 80 ? 'var(--emerald)' : conf >= 60 ? 'var(--amber)' : 'var(--indigo)',
                              animationDelay: `${idx * 0.06 + 0.3}s`,
                            }}
                          />
                        </div>
                        <span style={{ fontSize: 11, fontWeight: 700, color: conf >= 80 ? 'var(--emerald)' : conf >= 60 ? 'var(--amber)' : 'var(--indigo-light)', flexShrink: 0 }}>
                          {conf}%
                        </span>
                      </div>

                      {/* Meta chips */}
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                        {action.owner && (
                          <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(99,102,241,0.12)', color: 'var(--indigo-light)', border: '1px solid rgba(99,102,241,0.25)' }}>
                            {action.owner}
                          </span>
                        )}
                        {action.priority && (
                          <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(16,185,129,0.1)', color: 'var(--emerald)', border: '1px solid rgba(16,185,129,0.2)' }}>
                            {action.priority}
                          </span>
                        )}
                        {action.estimated_hours && (
                          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>~{action.estimated_hours}h</span>
                        )}
                      </div>

                      {/* Reasoning summary (top action only) */}
                      {isTop && action.reasoning_summary && (
                        <div style={{ marginTop: 10, padding: '8px 12px', background: 'rgba(99,102,241,0.07)', borderRadius: 'var(--radius-sm)', borderLeft: '2px solid rgba(99,102,241,0.4)' }}>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Agent reasoning</div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontStyle: 'italic', lineHeight: 1.6 }}>
                            {action.reasoning_summary}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* CTA after cards */}
          {visibleCards >= (nbaData.actions?.length || 0) && nbaData.actions?.length > 0 && (
            <div className="fade-in" style={{ marginTop: 20, display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button className="btn btn-ghost" onClick={handleReset}>← New Interaction</button>
              {nbaId && (
                <button className="btn btn-primary btn-lg" onClick={() => router.push(`/nba/${nbaId}`)}>
                  View Full Analysis & Approve →
                </button>
              )}
            </div>
          )}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
