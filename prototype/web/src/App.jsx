import { useCallback, useEffect, useState } from 'react'
import { Activity } from './Activity.jsx'
import { api } from './api.js'
import { Approvals } from './Approvals.jsx'
import { Chat } from './Chat.jsx'
import { Memory, Rules, Setup } from './Panels.jsx'
import { Providers } from './Providers.jsx'

const TABS = [['chat', 'Chat'], ['approvals', 'Approvals'], ['activity', 'Activity'], ['memory', 'Memory'], ['rules', 'Rules'], ['setup', 'Setup'], ['providers', 'Providers']]

export function App() {
  const [tab, setTab] = useState('chat')
  const [actions, setActions] = useState(null)
  const reload = useCallback(() => api('/api/actions').then(setActions).catch(() => {}), [])
  // Pending count: refreshed on opening the tab, and every 10 s only while the page is visible.
  useEffect(() => { reload() }, [tab, reload])
  useEffect(() => {
    const t = setInterval(() => { if (document.visibilityState === 'visible') reload() }, 10000)
    return () => clearInterval(t)
  }, [reload])
  const pending = actions?.length || 0
  const onKey = (e) => {
    const i = TABS.findIndex(([id]) => id === tab)
    const j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: TABS.length - 1 }[e.key]
    if (j === undefined) return
    e.preventDefault()
    const id = TABS[(j + TABS.length) % TABS.length][0]
    setTab(id)
    document.getElementById(`tab-${id}`)?.focus()
  }
  return (
    <div className="shell">
      <header className="top">
        <span className="brand">PAI</span>
        <div className="tabs" role="tablist" aria-label="Sections" onKeyDown={onKey}>
          {TABS.map(([id, label]) => (
            <button key={id} id={`tab-${id}`} role="tab" aria-selected={tab === id} aria-current={tab === id} aria-controls="view" tabIndex={tab === id ? 0 : -1} onClick={() => setTab(id)}>
              {label}{id === 'approvals' && pending > 0 && <span className="badge" aria-label={`${pending} waiting`}>{pending}</span>}
            </button>
          ))}
        </div>
      </header>
      <main className="body" id="view" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === 'chat' && <Chat />}
        {tab === 'approvals' && <Approvals actions={actions} reload={reload} />}
        {tab === 'activity' && <Activity />}
        {tab === 'setup' && <Setup onDone={() => setTab('rules')} />}
        {tab === 'rules' && <Rules />}
        {tab === 'memory' && <Memory />}
        {tab === 'providers' && <Providers />}
      </main>
    </div>
  )
}
