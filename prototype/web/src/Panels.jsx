import { useEffect, useState } from 'react'
import { Mic, RotateCcw } from 'lucide-react'
import { api } from './api.js'
import { shouldSubmitOnEnter } from './format.js'
import { useRecorder } from './useRecorder.js'

const PRESETS = {
  name: ['Sam', 'Alex', 'Jordan'],
  work: [
    'Founder and operator running local AI infrastructure and mortgage operations.',
    'Software architect building privacy-first systems.',
    'Executive managing product, engineering, and client workflows.',
  ],
  apps: [
    'Calendar, Mail (Himalaya/IMAP), Notes, Terminal, and Browser.',
    'Telegram, Signal, Local Docs (Seafile), and Git.',
    'Email, Calendar, Tasks (Paperclip), and Voice.',
  ],
  help: [
    'Triage inbound messages, draft replies, track tasks, and recall local notes.',
    'Summarize daily priorities, guard focus time, and organize project memory.',
    'Run browser research in Rakazo sandbox and prepare executive briefings.',
  ],
  off_limits: [
    'Never send emails, move money, or delete records without my explicit approval.',
    'Never send sensitive client data or long IDs to any external cloud model.',
    'Never modify system rules or approve risky actions autonomously.',
  ],
  tone: [
    'Short and direct — lead with the answer, no filler.',
    'Concise technical bullets with exact commands and numbers.',
    'Clear and direct with actionable next steps.',
  ],
  schedule: [
    'Active 8am–7pm PT; quiet after 8pm unless urgent.',
    'Weekdays 7am–6pm; hold non-urgent notifications on weekends.',
    'On-demand when I message you; no unsolicited pings at night.',
  ],
  people: [
    'Mona (Ops), Kristen (Client Mgr), Eve (Compliance), Miguel (LO).',
    'Engineering team, design partners, and family.',
    'Core ops team and direct clients.',
  ],
}

const DEMO_PROFILE = {
  name: 'Sam',
  work: 'Founder and operator running local AI infrastructure and mortgage operations.',
  apps: 'Calendar, Mail (Himalaya/IMAP), Notes, Paperclip, and Rakazo Browser.',
  help: 'Triage inbound messages, draft replies, track tasks, and recall local memory.',
  off_limits: 'Never send emails, delete data, or execute outward actions without explicit approval.',
  tone: 'Short and direct — lead with the result, no filler.',
  schedule: 'Active 8am–7pm PT; stay quiet after 8pm unless I reach out first.',
  people: 'Mona (Ops), Summer (LO Asst), Kristen (Client Mgr), Eve (UW/Compliance).',
}

export function Setup({ onDone, onStatusChange }) {
  const [s, setS] = useState(null)
  const [onb, setOnb] = useState(null)
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [step, setStep] = useState(1)

  const load = async () => {
    try {
      const [iv, ob] = await Promise.all([
        api('/api/interview'),
        api('/api/onboarding').catch(() => null),
      ])
      setS(iv)
      if (ob) {
        setOnb(ob)
        if (iv.done && ob.rules_ready) setStep(3)
        else if (iv.answered > 0 || iv.done) setStep(2)
      }
      onStatusChange?.()
    } catch (e) {
      setErr(e.message)
    }
  }

  useEffect(() => { load() }, [])

  const { recording, toggle } = useRecorder(async (blob) => {
    const fd = new FormData()
    fd.append('audio', blob, 'speech.webm')
    const r = await fetch('/api/transcribe', { method: 'POST', body: fd }).then((x) => x.json())
    setAnswer(r.text || '')
  })

  if (!s) return <div className="panel">{err || 'Loading setup…'}</div>

  const next = async (valOverride) => {
    const val = (typeof valOverride === 'string' ? valOverride : answer).trim()
    if (!val || busy) return
    setErr('')
    setBusy(true)
    try {
      const updated = await api('/api/interview', { method: 'POST', body: JSON.stringify({ key: s.key, value: val }) })
      setS(updated)
      setAnswer('')
      const ob = await api('/api/onboarding').catch(() => null)
      if (ob) setOnb(ob)
      onStatusChange?.()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  const onAnswerKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (shouldSubmitOnEnter(e)) next()
    }
  }

  const quickFillAll = async () => {
    setBusy(true)
    setErr('')
    try {
      for (const [k, v] of Object.entries(DEMO_PROFILE)) {
        await api('/api/interview', { method: 'POST', body: JSON.stringify({ key: k, value: v }) })
      }
      await load()
      setStep(2)
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  const draft = async () => {
    setBusy(true)
    setErr('')
    try {
      await api('/api/rules/draft', { method: 'POST' })
      await load()
      onDone()
    } catch (e) {
      try {
        const fallbackRules = `I will:\n- Run inference, voice transcription, and memory search locally on this machine.\n- Help ${onb?.questions?.find((q) => q.key === 'name')?.answer || 'you'} with: ${onb?.questions?.find((q) => q.key === 'help')?.answer || 'daily operations and memory recall'}.\n- Communicate in your preferred style: ${onb?.questions?.find((q) => q.key === 'tone')?.answer || 'short and direct'}.\n\nI won't:\n- ${onb?.questions?.find((q) => q.key === 'off_limits')?.answer || 'Never send, delete, or spend anything without explicit approval in Approvals.'}\n- Never transmit raw memories, profile data, or long identifiers to external cloud APIs.`
        await api('/api/rules', { method: 'PUT', body: JSON.stringify({ text: fallbackRules }) })
        await load()
        onDone()
      } catch {
        setErr(e.message)
      }
    } finally {
      setBusy(false)
    }
  }

  const resetWizard = async () => {
    setBusy(true)
    setErr('')
    try {
      await api('/api/onboarding/reset', { method: 'POST' })
      setAnswer('')
      setStep(1)
      await load()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  const suggestions = (s.key && PRESETS[s.key]) || []

  return (
    <section className="panel onboarding-wizard">
      <div className="wiz-header">
        <div>
          <h2>Initial System Setup</h2>
          <p className="muted">
            Configure your local assistant. No cloud accounts or external API keys are required; your answers and memory stay on this machine.
          </p>
        </div>
        {(s.answered > 0 || onb?.rules_ready) && (
          <button type="button" className="btn btn-sm" onClick={resetWizard} disabled={busy}>
            <RotateCcw size={14} style={{ verticalAlign: -2 }} /> Reset setup
          </button>
        )}
      </div>

      <div className="wiz-steps" role="tablist" aria-label="Setup steps">
        <button type="button" role="tab" aria-selected={step === 1} className={`wiz-step ${step === 1 ? 'active' : 'done'}`} onClick={() => setStep(1)}>
          <span className="step-num">1</span>
          <div>
            <strong>Local Runtime</strong>
            <span>Models, voice, and storage</span>
          </div>
        </button>
        <button type="button" role="tab" aria-selected={step === 2} className={`wiz-step ${step === 2 ? 'active' : s.done ? 'done' : ''}`} onClick={() => setStep(2)}>
          <span className="step-num">2</span>
          <div>
            <strong>Owner Profile ({s.answered}/{s.total})</strong>
            <span>Working context and boundaries</span>
          </div>
        </button>
        <button type="button" role="tab" aria-selected={step === 3} className={`wiz-step ${step === 3 ? 'active' : onb?.rules_ready ? 'done' : ''}`} onClick={() => setStep(3)}>
          <span className="step-num">3</span>
          <div>
            <strong>Operating Rules</strong>
            <span>Review and activate</span>
          </div>
        </button>
      </div>

      {step === 1 && (
        <div className="wiz-stage">
          <div className="ledger" role="table" aria-label="Local runtime services">
            <div className="ledger-row" role="row">
              <div className="ledger-main" role="cell">
                <strong>Language Model (llama.cpp)</strong>
                <span className="muted">Local inference for chat and routing via <code>{onb?.local_stack?.llm || 'pai-chat'}</code> (Qwen3-4B GGUF)</span>
              </div>
              <div className="ledger-meta" role="cell">
                <code>127.0.0.1:8080</code>
                <span className="status-tag">Ready · Local</span>
              </div>
            </div>
            <div className="ledger-row" role="row">
              <div className="ledger-main" role="cell">
                <strong>Speech Engine (Speaches)</strong>
                <span className="muted">Dictation via Faster-Whisper Small; spoken replies via Kokoro-82M (<code>{onb?.local_stack?.voice || 'af_heart'}</code>)</span>
              </div>
              <div className="ledger-meta" role="cell">
                <code>127.0.0.1:8000</code>
                <span className="status-tag">Ready · Local</span>
              </div>
            </div>
            <div className="ledger-row" role="row">
              <div className="ledger-main" role="cell">
                <strong>Memory &amp; Audit Store</strong>
                <span className="muted">SQLite FTS5 + BGE-Small vector recall with SHA-256 hash-chained activity log</span>
              </div>
              <div className="ledger-meta" role="cell">
                <code>/data/pai.db</code>
                <span className="status-tag">Encrypted</span>
              </div>
            </div>
            <div className="ledger-row" role="row">
              <div className="ledger-main" role="cell">
                <strong>Outbound Network Policy</strong>
                <span className="muted">Loopback-bound web interface; external cloud routing disabled by default</span>
              </div>
              <div className="ledger-meta" role="cell">
                <code>127.0.0.1:8088</code>
                <span className="status-tag">{onb?.local_stack?.cloud_enabled ? 'Cloud optional' : 'Local only'}</span>
              </div>
            </div>
          </div>

          <div className="row" style={{ justifyContent: 'space-between', marginTop: 8 }}>
            <button type="button" className="btn" onClick={quickFillAll} disabled={busy}>
              Fill sample profile
            </button>
            <button type="button" className="btn primary" onClick={() => setStep(2)}>
              Continue to profile →
            </button>
          </div>
        </div>
      )}

      {step !== 1 && (
        <div className="wiz-interview-layout">
          <div className="wiz-q-rail">
            <div className="rail-head">
              <strong>Profile questions</strong>
              <span className="muted">{s.answered} of {s.total} answered</span>
            </div>
            <div className="bar" aria-hidden><i style={{ width: `${(s.answered / s.total) * 100}%` }} /></div>
            <div className="q-list">
              {(onb?.questions || []).map((q, idx) => {
                const isCurrent = s.key === q.key && !s.done
                const isAnswered = Boolean(q.answer)
                return (
                  <div key={q.key} className={`q-item ${isCurrent ? 'current' : ''} ${isAnswered ? 'answered' : ''}`}>
                    <span className="q-idx">{isAnswered ? '✓' : idx + 1}</span>
                    <div className="q-meta">
                      <div className="q-title">{q.question}</div>
                      {q.answer && <div className="q-ans">{q.answer}</div>}
                    </div>
                  </div>
                )
              })}
            </div>
            {!s.done && (
              <button type="button" className="btn btn-sm" onClick={quickFillAll} disabled={busy}>
                Fill all 8 with sample answers
              </button>
            )}
          </div>

          <div className="wiz-q-main">
            {s.done ? (
              <div className="done-card">
                <h3>Generate Operating Rules</h3>
                <p className="muted">
                  All 8 profile questions are saved. PAI will now draft a plain-language set of operating rules from your answers using the local model.
                </p>
                <div className="row" style={{ marginTop: 8 }}>
                  <button type="button" className="btn primary" onClick={draft} disabled={busy}>
                    {busy ? 'Drafting rules locally…' : 'Draft my rules'}
                  </button>
                  {onb?.rules_ready && (
                    <button type="button" className="btn" onClick={onDone}>
                      Open workspace →
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <form className="question-card" onSubmit={(e) => { e.preventDefault(); next() }}>
                <div className="q-step-meta muted">Question {s.answered + 1} of {s.total}</div>
                <label htmlFor="ans" className="q-prompt"><strong>{s.question}</strong></label>
                <textarea
                  id="ans"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={onAnswerKeyDown}
                  placeholder="Type your answer, select a suggestion below, or use Speak to dictate…"
                />
                {suggestions.length > 0 && (
                  <div className="preset-group">
                    <span className="muted" style={{ fontSize: 12 }}>Suggestions:</span>
                    <div className="preset-pills">
                      {suggestions.map((p) => (
                        <button key={p} type="button" className="chip btn-chip" onClick={() => setAnswer(p)}>
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <div className="row" style={{ marginTop: 6 }}>
                  <button type="submit" className="btn primary" disabled={busy}>Save &amp; next</button>
                  <button type="button" className={`btn ${recording ? 'primary' : ''}`} onClick={toggle} aria-label="Answer by voice">
                    <Mic size={15} style={{ verticalAlign: -2 }} /> {recording ? 'Stop recording' : 'Speak'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {err && <p className="muted" role="alert" style={{ color: 'var(--danger)' }}>{err}</p>}
    </section>
  )
}

export function Rules() {
  const [text, setText] = useState('')
  const [status, setStatus] = useState('')
  useEffect(() => { api('/api/rules').then((r) => setText(r.text)) }, [])
  const save = async () => {
    await api('/api/rules', { method: 'PUT', body: JSON.stringify({ text }) })
    setStatus('Saved to local database.')
  }
  return (
    <section className="panel">
      <div>
        <h2>Operating Rules</h2>
        <p className="muted">Included in every local system prompt. Edit at any time.</p>
      </div>
      <label htmlFor="rules-editor" className="sr-only">Operating rules</label>
      <textarea
        id="rules-editor"
        style={{ minBlockSize: '12lh' }}
        value={text}
        onChange={(e) => { setText(e.target.value); setStatus('') }}
        placeholder="Complete initial setup to generate a draft, or write your rules directly."
      />
      <div className="row">
        <button type="button" className="btn primary" onClick={save}>Save rules</button>
        <span className="muted" role="status" aria-live="polite">{status}</span>
      </div>
    </section>
  )
}

export function Memory() {
  const [list, setList] = useState(null)
  const [newMem, setNewMem] = useState('')
  const [busy, setBusy] = useState(false)
  const load = () => api('/api/memories').then(setList)
  useEffect(() => { load() }, [])
  const forget = async (id) => { await api(`/api/memories/${id}`, { method: 'DELETE' }); load() }
  const addQuick = async (e) => {
    e.preventDefault()
    if (!newMem.trim() || busy) return
    setBusy(true)
    try {
      await api('/api/chat', { method: 'POST', body: JSON.stringify({ message: `remember ${newMem.trim()}`, history: [] }) })
      setNewMem('')
      load()
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="panel">
      <div>
        <h2>Stored Memories</h2>
        <p className="muted">Facts stored in local SQLite and indexed for hybrid keyword + vector retrieval.</p>
      </div>
      <form className="row" onSubmit={addQuick}>
        <label htmlFor="new-memory-input" className="sr-only">New memory fact</label>
        <input
          id="new-memory-input"
          value={newMem}
          onChange={(e) => setNewMem(e.target.value)}
          placeholder="Add a fact to remember (e.g., Client call order is Mona, Summer, then Sam)…"
        />
        <button type="submit" className="btn primary" disabled={busy}>Add memory</button>
      </form>
      {!list ? (
        <p className="muted">Loading…</p>
      ) : list.length === 0 ? (
        <p className="muted">No memories stored yet. Say “remember …” in Chat or add a fact above.</p>
      ) : (
        <div className="ledger">
          {list.map((m) => (
            <div className="mem" key={m.id}>
              <div>
                <code>#{m.id}</code> <span>{m.text}</span>
                {m.created && <div className="muted" style={{ fontSize: 12 }}>{new Date(m.created).toLocaleString()}</div>}
              </div>
              <button type="button" className="btn btn-sm" onClick={() => forget(m.id)}>Remove</button>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
