import { useCallback, useEffect, useState } from 'react'
import { Activity } from './Activity.jsx'
import { api } from './api.js'
import { Approvals } from './Approvals.jsx'
import { Chat } from './Chat.jsx'
import { Memory, Rules, Setup } from './Panels.jsx'
import { Providers } from './Providers.jsx'

const TABS = [
  ['setup', 'Setup'],
  ['chat', 'Hermes'],
  ['rakazo', 'Rakazo'],
  ['paperclip', 'Paperclip'],
  ['approvals', 'Approvals'],
  ['activity', 'Activity'],
  ['memory', 'Memory'],
  ['rules', 'Rules'],
  ['providers', 'Runtime'],
]

export function RakazoWorkspace({ actions, reload }) {
  const [simStatus, setSimStatus] = useState('')
  const [simBusy, setSimBusy] = useState(false)

  const triggerSimulatedAction = async (label, promptText) => {
    setSimBusy(true)
    setSimStatus(`Staging "${label}" in Rakazo sandbox…`)
    try {
      const mems = await api('/api/memories')
      let targetId = mems?.[0]?.id
      if (!targetId) {
        await api('/api/chat', {
          method: 'POST',
          body: JSON.stringify({ message: `remember [Sandbox item] ${label} staged for review`, history: [] }),
        })
        const updated = await api('/api/memories')
        targetId = updated?.[0]?.id
      }
      if (targetId) {
        const res = await api('/api/chat', {
          method: 'POST',
          body: JSON.stringify({ message: `delete memory ${targetId}`, history: [] }),
        })
        setSimStatus(res.reply || `Action staged in Approvals (${promptText}).`)
      }
      await reload()
    } catch (e) {
      setSimStatus(`Error: ${e.message}`)
    }
    setSimBusy(false)
  }

  return (
    <div className="rakazo-workspace">
      <div className="panel rakazo-hero">
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2>Rakazo Action Gate &amp; Audit Workspace</h2>
            <p className="muted" style={{ margin: '4px 0 0' }}>
              State-mutating operations, memory deletions, and outbound dispatches pause here for explicit confirmation before execution.
            </p>
          </div>
          <div className="row">
            <button
              type="button"
              className="btn primary"
              disabled={simBusy}
              onClick={() => triggerSimulatedAction('Purge stale sandbox record', 'tier3_destructive_gate')}
            >
              {simBusy ? 'Staging action…' : 'Stage sample action'}
            </button>
          </div>
        </div>
        {simStatus && (
          <div className="banner" style={{ marginTop: '8px' }} role="status">
            <span style={{ fontSize: '13px' }}>{simStatus}</span>
            <button type="button" className="btn btn-sm" onClick={() => setSimStatus('')}>Dismiss</button>
          </div>
        )}
      </div>

      <div className="rakazo-split">
        <div className="rakazo-col">
          <Approvals actions={actions} reload={reload} />
        </div>
        <div className="rakazo-col">
          <Activity refreshKey={actions?.length || 0} />
        </div>
      </div>
    </div>
  )
}

export function PaperclipBoard({ actions, onboarding, onNavigate }) {
  const [memories, setMemories] = useState([])
  const [rules, setRules] = useState({ text: '' })
  const [tasks, setTasks] = useState([
    { id: 't-1', title: 'Local LLM inference server (Qwen3-4B GGUF)', agent: 'Platform', lane: 'done', tag: 'llama.cpp :8080' },
    { id: 't-2', title: 'Local speech pipeline (Faster-Whisper + Kokoro)', agent: 'Voice', lane: 'done', tag: 'Speaches :8000' },
    { id: 't-3', title: 'Hybrid FTS5 + BGE-Small memory indexing', agent: 'Storage', lane: 'active', tag: 'SQLite' },
    { id: 't-4', title: 'Action approval gate & SHA-256 audit verification', agent: 'Policy', lane: 'active', tag: 'Governance' },
  ])
  const [newTaskTitle, setNewTaskTitle] = useState('')

  useEffect(() => {
    api('/api/memories').then(setMemories).catch(() => {})
    api('/api/rules').then(setRules).catch(() => {})
  }, [])

  const addTask = (e) => {
    e.preventDefault()
    if (!newTaskTitle.trim()) return
    setTasks((prev) => [
      { id: `t-${Date.now()}`, title: newTaskTitle.trim(), agent: 'Operator', lane: 'backlog', tag: 'Task' },
      ...prev,
    ])
    setNewTaskTitle('')
  }

  const moveTask = (id, nextLane) => {
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, lane: nextLane } : t)))
  }

  const backlog = tasks.filter((t) => t.lane === 'backlog')
  const active = tasks.filter((t) => t.lane === 'active')
  const done = tasks.filter((t) => t.lane === 'done')
  const pendingActions = actions || []

  return (
    <div className="paperclip-shell">
      <div className="panel" style={{ marginBottom: '14px' }}>
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>Paperclip Task &amp; Governance Board</h2>
            <p className="muted" style={{ margin: '4px 0 0' }}>
              Track local workstreams, review pending approvals ({pendingActions.length}), and inspect stored memories ({memories.length}).
            </p>
          </div>
          <form className="row" onSubmit={addTask}>
            <label htmlFor="paperclip-new-task" className="sr-only">New task title</label>
            <input
              id="paperclip-new-task"
              placeholder="Add a task…"
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              style={{ minWidth: '220px' }}
            />
            <button type="submit" className="btn primary">Add task</button>
          </form>
        </div>
      </div>

      <div className="paperclip-board">
        <div className="kanban-col">
          <div className="kanban-head">
            <strong>Setup &amp; Rules</strong>
            <span className="status-tag">{onboarding?.answered ?? 0}/{onboarding?.total ?? 8}</span>
          </div>
          <div className="kanban-card">
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong>Owner Profile</strong>
              <span className="status-tag">{onboarding?.done ? 'Complete' : 'Pending'}</span>
            </div>
            <p className="muted" style={{ fontSize: '12.5px', margin: '2px 0 6px' }}>
              {onboarding?.done
                ? 'All 8 calibration questions saved locally.'
                : `${onboarding?.answered ?? 0} of 8 profile questions answered.`}
            </p>
            <button type="button" className="btn btn-sm" onClick={() => onNavigate('setup')}>
              {onboarding?.done ? 'Review setup' : 'Continue setup →'}
            </button>
          </div>

          <div className="kanban-card">
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong>Operating Rules</strong>
              <span className="status-tag">SQLite</span>
            </div>
            <p className="muted" style={{ fontSize: '12px', margin: '2px 0 6px', whiteSpace: 'pre-wrap' }}>
              {rules?.text ? rules.text.slice(0, 120) + (rules.text.length > 120 ? '…' : '') : 'No custom rules saved yet.'}
            </p>
            <button type="button" className="btn btn-sm" onClick={() => onNavigate('rules')}>
              Edit rules
            </button>
          </div>

          {backlog.map((t) => (
            <div key={t.id} className="kanban-card">
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <span className="status-tag">{t.tag}</span>
                <span className="muted" style={{ fontSize: '11.5px' }}>{t.agent}</span>
              </div>
              <strong>{t.title}</strong>
              <div className="row" style={{ marginTop: '4px' }}>
                <button type="button" className="btn btn-sm" onClick={() => moveTask(t.id, 'active')}>
                  Move to active →
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="kanban-col">
          <div className="kanban-head">
            <strong>Active Workstreams</strong>
            <span className="status-tag">{active.length}</span>
          </div>
          {active.map((t) => (
            <div key={t.id} className="kanban-card">
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <span className="status-tag">{t.tag}</span>
                <span className="muted" style={{ fontSize: '11.5px' }}>{t.agent}</span>
              </div>
              <strong>{t.title}</strong>
              <div className="row" style={{ marginTop: '4px' }}>
                <button type="button" className="btn btn-sm" onClick={() => moveTask(t.id, 'done')}>
                  Mark complete
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="kanban-col">
          <div className="kanban-head">
            <strong>Approval Gate</strong>
            <span className="status-tag">{pendingActions.length}</span>
          </div>
          {pendingActions.length === 0 ? (
            <div className="kanban-card">
              <strong>No Pending Approvals</strong>
              <p className="muted" style={{ fontSize: '12.5px', margin: '2px 0 6px' }}>
                No high-risk actions are waiting for confirmation.
              </p>
              <button type="button" className="btn btn-sm" onClick={() => onNavigate('rakazo')}>
                Open Rakazo workspace
              </button>
            </div>
          ) : (
            pendingActions.map((a) => (
              <div key={a.id} className="kanban-card" style={{ borderColor: 'var(--danger)' }}>
                <span className="status-tag" style={{ color: 'var(--danger)' }}>Needs confirmation</span>
                <strong>{a.summary}</strong>
                <button type="button" className="btn btn-sm primary" style={{ marginTop: '4px' }} onClick={() => onNavigate('approvals')}>
                  Review in Approvals →
                </button>
              </div>
            ))
          )}
        </div>

        <div className="kanban-col">
          <div className="kanban-head">
            <strong>Verified Services</strong>
            <span className="status-tag">{done.length}</span>
          </div>
          {done.map((t) => (
            <div key={t.id} className="kanban-card">
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <span className="status-tag">Online</span>
                <span className="muted" style={{ fontSize: '11.5px' }}>{t.agent}</span>
              </div>
              <strong>{t.title}</strong>
              <code style={{ fontSize: '11.5px', width: 'fit-content' }}>{t.tag}</code>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function App() {
  const [tab, setTab] = useState('chat')
  const [actions, setActions] = useState(null)
  const [onboarding, setOnboarding] = useState(null)
  const [checkedBoot, setCheckedBoot] = useState(false)

  const reload = useCallback(() => {
    api('/api/actions').then(setActions).catch(() => {})
    api('/api/onboarding')
      .then((ob) => {
        setOnboarding(ob)
        if (!checkedBoot) {
          setCheckedBoot(true)
          if (!ob.done) setTab('setup')
        }
      })
      .catch(() => {
        api('/api/interview')
          .then((iv) => {
            setOnboarding(iv)
            if (!checkedBoot) {
              setCheckedBoot(true)
              if (!iv.done) setTab('setup')
            }
          })
          .catch(() => {})
      })
  }, [checkedBoot])

  useEffect(() => { reload() }, [tab, reload])
  useEffect(() => {
    const t = setInterval(() => { if (document.visibilityState === 'visible') reload() }, 10000)
    return () => clearInterval(t)
  }, [reload])

  const pending = actions?.length || 0
  const needsOnboarding = onboarding && !onboarding.done

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
        <div className="brand-cluster">
          <span className="brand-mark" aria-hidden="true" />
          <div>
            <span className="brand">PAI OS</span>
            <span className="brand-sub">Local Personal AI</span>
          </div>
        </div>
        <div className="tabs" role="tablist" aria-label="Sections" onKeyDown={onKey}>
          {TABS.map(([id, label]) => (
            <button
              key={id}
              id={`tab-${id}`}
              type="button"
              role="tab"
              aria-selected={tab === id}
              aria-current={tab === id}
              aria-controls="view"
              tabIndex={tab === id ? 0 : -1}
              onClick={() => setTab(id)}
            >
              {label}
              {id === 'setup' && needsOnboarding && (
                <span className="badge neutral-badge" aria-label="Setup progress">
                  {onboarding.answered}/{onboarding.total}
                </span>
              )}
              {(id === 'approvals' || id === 'rakazo') && pending > 0 && (
                <span className="badge" aria-label={`${pending} waiting`}>{pending}</span>
              )}
            </button>
          ))}
        </div>
      </header>

      {needsOnboarding && tab !== 'setup' && (
        <div className="boot-banner" role="region" aria-label="Setup reminder">
          <div>
            <strong>Initial setup incomplete ({onboarding.answered} of {onboarding.total} answered)</strong>
            <span className="muted" style={{ marginLeft: '10px' }}>
              Finish the 8-question local interview so PAI can draft your operating rules.
            </span>
          </div>
          <button type="button" className="btn btn-sm primary" onClick={() => setTab('setup')}>
            Continue setup →
          </button>
        </div>
      )}

      <main className="body" id="view" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === 'chat' && <Chat onNavigate={setTab} />}
        {tab === 'rakazo' && <RakazoWorkspace actions={actions} reload={reload} />}
        {tab === 'paperclip' && <PaperclipBoard actions={actions} onboarding={onboarding} onNavigate={setTab} />}
        {tab === 'approvals' && <Approvals actions={actions} reload={reload} />}
        {tab === 'activity' && <Activity />}
        {tab === 'setup' && <Setup onDone={() => { reload(); setTab('chat') }} />}
        {tab === 'rules' && <Rules />}
        {tab === 'memory' && <Memory />}
        {tab === 'providers' && <Providers />}
      </main>
    </div>
  )
}
