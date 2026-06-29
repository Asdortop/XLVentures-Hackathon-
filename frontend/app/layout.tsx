'use client'
import { useState, useEffect, createContext, useContext } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import './globals.css'

interface Domain { id: number; slug: string; name: string; label: string; entity_label: string }
interface AppCtx { domain: Domain | null; domains: Domain[]; setDomain: (d: Domain) => void }

export const AppContext = createContext<AppCtx>({ domain: null, domains: [], setDomain: () => {} })
export const useApp = () => useContext(AppContext)

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [domains, setDomains] = useState<Domain[]>([])
  const [domain, setDomain] = useState<Domain | null>(null)
  const [showDD, setShowDD] = useState(false)
  const [pendingCount, setPendingCount] = useState(0)
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    fetch('/api/domains').then(r => r.json()).then((data: Domain[]) => {
      setDomains(data)
      const saved = localStorage.getItem('active_domain_id')
      const found = saved ? data.find(d => d.id === +saved) : null
      setDomain(found || data[0] || null)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!domain) return
    fetch(`/api/nba/${domain.id}?status=pending`).then(r => r.json()).then((data: any[]) => {
      setPendingCount(data.length)
    }).catch(() => {})
  }, [domain, pathname])

  const switchDomain = (d: Domain) => {
    setDomain(d)
    localStorage.setItem('active_domain_id', String(d.id))
    setShowDD(false)
  }

  const navItems = [
    { href: '/', icon: '⬡', label: 'Command Center' },
    { href: '/interact', icon: '✦', label: 'Submit Interaction' },
    { href: '/nba', icon: '◈', label: 'NBA Inbox', badge: pendingCount },
    { href: '/outcomes', icon: '◎', label: 'Outcomes' },
    { href: '/onboarding', icon: '⊕', label: 'Add Domain' },
  ]

  return (
    <html lang="en">
      <head>
        <title>Praxis AI — Decision Intelligence</title>
        <meta name="description" content="Agentic B2B Decision Intelligence Platform" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body>
        <AppContext.Provider value={{ domain, domains, setDomain: switchDomain }}>
          <div className="app-shell">
            {/* Sidebar */}
            <aside className="sidebar">
              <div className="sidebar-logo">
                <div className="sidebar-logo-mark">
                  <div className="logo-icon">P</div>
                  <div>
                    <div className="logo-text">Praxis AI</div>
                    <div className="logo-sub">Decision Intelligence</div>
                  </div>
                </div>
              </div>

              {/* Domain Switcher */}
              <div style={{ padding: '12px', position: 'relative' }}>
                <div className="domain-switcher" onClick={() => setShowDD(!showDD)}>
                  <div className="domain-switcher-label">Active Domain</div>
                  <div className="domain-switcher-name">
                    <span>{domain?.label || 'Select domain...'}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{showDD ? '▲' : '▼'}</span>
                  </div>
                </div>
                {showDD && (
                  <div className="domain-dropdown">
                    {domains.map(d => (
                      <div key={d.id} className={`domain-option ${domain?.id === d.id ? 'selected' : ''}`} onClick={() => switchDomain(d)}>
                        {d.label}
                      </div>
                    ))}
                    <div style={{ borderTop: '1px solid var(--border)', marginTop: 6, paddingTop: 6 }}>
                      <Link href="/onboarding">
                        <div className="domain-option" onClick={() => setShowDD(false)} style={{ color: 'var(--indigo-light)' }}>
                          ⊕ Add new domain
                        </div>
                      </Link>
                    </div>
                  </div>
                )}
              </div>

              {/* Nav */}
              <div className="sidebar-section">
                <div className="sidebar-section-label">Navigation</div>
                {navItems.map(item => (
                  <Link key={item.href} href={item.href}>
                    <button className={`nav-item ${pathname === item.href ? 'active' : ''}`}>
                      <span className="nav-icon">{item.icon}</span>
                      <span>{item.label}</span>
                      {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
                    </button>
                  </Link>
                ))}
              </div>

              {/* Pipeline indicator */}
              <div style={{ marginTop: 'auto', padding: '16px 12px', borderTop: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Agent Pipeline</div>
                {['Planner', 'Context', 'Dependency', 'Risk', 'Recommender'].map((a, i) => (
                  <div key={a} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--indigo)', opacity: 0.7 }} />
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{a}</span>
                  </div>
                ))}
              </div>
            </aside>

            {/* Main */}
            <main className="main-content">
              {children}
            </main>
          </div>
        </AppContext.Provider>
      </body>
    </html>
  )
}
