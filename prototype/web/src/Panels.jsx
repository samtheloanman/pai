import { useEffect, useRef, useState } from 'react'
import { Mic } from 'lucide-react'
import { api } from './api.js'
import { useRecorder } from './useRecorder.js'

export function Setup({ onDone }) {
  const [s, setS] = useState(null)
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const load = () => api('/api/interview').then(setS).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [])
  const { recording, toggle } = useRecorder(async (blob) => {
    const fd = new FormData(); fd.append('audio', blob, 'speech.webm')
    const r = await fetch('/api/transcribe', { method: 'POST', body: fd }).then((x) => x.json())
    setAnswer(r.text || '') // nothing is saved until Next
  })
  if (!s) return <div className="panel">{err || 'Loading…'}</div>
  const next = async () => {
    if (!answer.trim()) return
    setErr('')
    try { setS(await api('/api/interview', { method: 'POST', body: JSON.stringify({ key: s.key, value: answer }) })); setAnswer('') }
    catch (e) { setErr(e.message) }
  }
  const draft = async () => {
    setBusy(true); setErr('')
    try { await api('/api/rules/draft', { method: 'POST' }); onDone() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <section className="panel">
      <h2>Getting to know you</h2>
      <div className="bar" aria-hidden><i style={{ width: `${(s.answered / s.total) * 100}%` }} /></div>
      <p className="muted">{s.answered} of {s.total} answered. Answers stay on this box.</p>
      {s.done ? (
        <>
          <p>All done. PAI will draft what it will and won't do; you can edit it next.</p>
          <div className="row"><button className="btn primary" onClick={draft} disabled={busy}>{busy ? 'Drafting…' : 'Draft my rules'}</button></div>
        </>
      ) : (
        <>
          <label htmlFor="ans"><strong>{s.question}</strong></label>
          <textarea id="ans" value={answer} onChange={(e) => setAnswer(e.target.value)} />
          <div className="row">
            <button className="btn primary" onClick={next}>Next</button>
            <button className={`btn ${recording ? 'primary' : ''}`} onClick={toggle} aria-label="Answer by voice"><Mic size={16} style={{ verticalAlign: -3 }} /> {recording ? 'Stop' : 'Speak'}</button>
          </div>
        </>
      )}
      {err && <p className="muted" role="alert" style={{ color: 'var(--danger)' }}>{err}</p>}
    </section>
  )
}

export function Rules() {
  const [text, setText] = useState('')
  const [status, setStatus] = useState('')
  useEffect(() => { api('/api/rules').then((r) => setText(r.text)) }, [])
  const save = async () => { await api('/api/rules', { method: 'PUT', body: JSON.stringify({ text }) }); setStatus('Saved') }
  return (
    <section className="panel">
      <h2>What PAI will and won't do</h2>
      <p className="muted">PAI follows this page. Edit anything.</p>
      <textarea style={{ minHeight: 280 }} aria-label="Rules" value={text} onChange={(e) => { setText(e.target.value); setStatus('') }} placeholder="Finish the setup interview to draft this page." />
      <div className="row"><button className="btn primary" onClick={save}>Save</button><span className="muted">{status}</span></div>
    </section>
  )
}

export function Memory() {
  const [list, setList] = useState(null)
  const load = () => api('/api/memories').then(setList)
  useEffect(() => { load() }, [])
  const forget = async (id) => { await api(`/api/memories/${id}`, { method: 'DELETE' }); load() }
  return (
    <section className="panel">
      <h2>What PAI remembers</h2>
      {!list ? <p className="muted">Loading…</p> : list.length === 0 ? <p className="muted">Nothing yet. In Chat, say “remember …”.</p> : list.map((m) => (
        <div className="mem" key={m.id}><span>{m.text}</span><button className="btn" onClick={() => forget(m.id)}>Forget</button></div>
      ))}
    </section>
  )
}
