import { useState } from 'react'
import { api } from './api.js'
import { riskLabel } from './format.js'

const WORDS = { done: 'Done.', expired: 'That request expired.', already_done: 'Already handled.', rejected: 'Rejected.', failed: 'That did not work.', unknown: 'Unknown request.' }

export function Approvals({ actions, reload }) {
  const [busy, setBusy] = useState(null)
  const [msg, setMsg] = useState('')
  const act = async (id, verb) => {
    if (busy) return
    setBusy(id); setMsg('')
    try {
      const r = await api(`/api/actions/${id}/${verb}`, { method: 'POST' })
      setMsg(verb === 'reject' ? 'Rejected.' : WORDS[r.status] || 'Unknown request.')
    } catch (e) { setMsg(e.message) }
    setBusy(null)
    reload()
  }
  return (
    <section className="panel">
      <div>
        <h2>Approvals</h2>
        <p className="muted" style={{ margin: '4px 0 0' }}>PAI asks before it sends, deletes, or spends anything.</p>
      </div>
      <p role="status" aria-live="polite" className="muted" style={msg ? { margin: 0 } : { display: 'none' }}>{msg}</p>
      {actions === null ? (
        <p className="muted" style={{ margin: 0 }}>Loading…</p>
      ) : actions.length === 0 ? (
        <p className="muted" style={{ margin: 0 }}>Nothing is waiting for you.</p>
      ) : (
        <div className="ledger">
          {actions.map((a) => (
            <div className="mem" key={a.id}>
              <div><span className="chip risk">{riskLabel(a.kind)}</span> <span>{a.summary}</span></div>
              <div className="row">
                <button type="button" className="btn primary" disabled={!!busy} onClick={() => act(a.id, 'confirm')} aria-label={`Approve: ${a.summary}`}>Approve</button>
                <button type="button" className="btn" disabled={!!busy} onClick={() => act(a.id, 'reject')} aria-label={`Reject: ${a.summary}`}>Reject</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
