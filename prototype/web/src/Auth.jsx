import { useCallback, useEffect, useState } from 'react'
import { api, SIGNED_OUT } from './api.js'

const MIN = 12

function Card({ title, children }) {
  return (
    <div className="shell">
      <main className="body">
        <div className="panel" style={{ maxWidth: 440, margin: '48px auto' }}>
          <h2>{title}</h2>
          {children}
        </div>
      </main>
    </div>
  )
}

function Field({ id, label, ...rest }) {
  return (
    <label htmlFor={id} style={{ display: 'grid', gap: 4 }}>
      <span>{label}</span>
      <input id={id} {...rest} />
    </label>
  )
}

function useSubmit(fn, done) {
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try { await fn(); done() } catch (x) { setErr(x.message) }
    setBusy(false)
  }
  return { err, busy, submit }
}

function CreateOwner({ done }) {
  const [p, setP] = useState('')
  const [q, setQ] = useState('')
  const { err, busy, submit } = useSubmit(async () => {
    if (p.length < MIN) throw new Error(`Use at least ${MIN} characters.`)
    if (p !== q) throw new Error('The two passphrases do not match.')
    await api('/api/auth/setup', { method: 'POST', body: JSON.stringify({ passphrase: p }) })
  }, done)
  return (
    <Card title="Create your passphrase">
      <p>This box has no owner yet. The passphrase protects your memories, rules and approvals. There is no recovery if you forget it, so write it down somewhere safe.</p>
      <form onSubmit={submit} style={{ display: 'grid', gap: 12 }}>
        <Field id="pass1" label={`Passphrase (${MIN}+ characters)`} type="password" autoComplete="new-password" value={p} onChange={(e) => setP(e.target.value)} />
        <Field id="pass2" label="Type it again" type="password" autoComplete="new-password" value={q} onChange={(e) => setQ(e.target.value)} />
        {err && <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>{err}</p>}
        <button type="submit" className="btn primary" disabled={busy}>Create and sign in</button>
      </form>
    </Card>
  )
}

function SignIn({ done }) {
  const [mode, setMode] = useState('pass')
  const [p, setP] = useState('')
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const { err, busy, submit } = useSubmit(async () => {
    if (mode === 'pass') await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ passphrase: p }) })
    else await api('/api/auth/pair', { method: 'POST', body: JSON.stringify({ code, name: name.trim() || 'New device' }) })
  }, done)
  return (
    <Card title={mode === 'pass' ? 'Sign in' : 'Pair this device'}>
      <form onSubmit={submit} style={{ display: 'grid', gap: 12 }}>
        {mode === 'pass'
          ? <Field id="pass" label="Passphrase" type="password" autoComplete="current-password" value={p} onChange={(e) => setP(e.target.value)} />
          : <>
              <p>On a device that is already signed in, open Devices and choose "Pair a new device". Enter the code it shows.</p>
              <Field id="code" label="Pairing code" autoComplete="one-time-code" autoCapitalize="characters" value={code} onChange={(e) => setCode(e.target.value)} placeholder="ABCDE-FGHJK" />
              <Field id="dname" label="Name for this device" maxLength={64} value={name} onChange={(e) => setName(e.target.value)} placeholder="My phone" />
            </>}
        {err && <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>{err}</p>}
        <button type="submit" className="btn primary" disabled={busy}>{mode === 'pass' ? 'Sign in' : 'Pair'}</button>
        <button type="button" className="btn" onClick={() => setMode(mode === 'pass' ? 'pair' : 'pass')}>
          {mode === 'pass' ? 'Pair with a code instead' : 'Use the passphrase instead'}
        </button>
      </form>
    </Card>
  )
}

/** Shows the owner setup or sign-in screen until the box says this browser is signed in. */
export function Gate({ children }) {
  const [s, setS] = useState(null)
  const [err, setErr] = useState('')
  const check = useCallback(() => {
    api('/api/auth/status').then((x) => { setS(x); setErr('') }).catch((e) => setErr(e.message))
  }, [])
  useEffect(() => {
    check()
    const out = () => setS((x) => (x ? { ...x, signed_in: false } : x))
    window.addEventListener(SIGNED_OUT, out)
    return () => window.removeEventListener(SIGNED_OUT, out)
  }, [check])
  if (!s) return <Card title="PAI">{err ? <p role="alert">Cannot reach this box: {err}</p> : <p>Loading…</p>}</Card>
  if (!s.owner) return <CreateOwner done={check} />
  if (!s.signed_in) return <SignIn done={check} />
  return children
}

export async function signOut() {
  await api('/api/auth/logout', { method: 'POST' }).catch(() => {})
  window.dispatchEvent(new Event(SIGNED_OUT))
}

const when = (t) => (t ? new Date(t * 1000).toLocaleString() : '—')

export function Devices() {
  const [list, setList] = useState(null)
  const [pair, setPair] = useState(null)
  const [err, setErr] = useState('')
  const load = useCallback(() => api('/api/devices').then(setList).catch((e) => setErr(e.message)), [])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (!pair) return undefined
    const t = setTimeout(() => setPair(null), pair.expires_in * 1000)
    return () => clearTimeout(t)
  }, [pair])
  const start = async () => {
    setErr('')
    try { setPair(await api('/api/devices/pairing', { method: 'POST' })) } catch (e) { setErr(e.message) }
  }
  const revoke = async (d) => {
    if (!window.confirm(`Remove ${d.name}? It will be signed out at once.`)) return
    try { await api(`/api/devices/${d.id}`, { method: 'DELETE' }); load() } catch (e) { setErr(e.message) }
  }
  return (
    <div className="panel">
      <h2>Devices</h2>
      <p>Phones and laptops paired with this box. Removing one signs it out at once.</p>
      <div className="row">
        <button type="button" className="btn primary" onClick={start}>Pair a new device</button>
        <button type="button" className="btn" onClick={signOut}>Sign out of this browser</button>
      </div>
      {pair && (
        <div className="mem" role="status" aria-live="polite">
          <p style={{ margin: 0 }}>On the new device, open this box's address, choose "Pair with a code instead" and enter:</p>
          <p style={{ fontSize: 28, letterSpacing: '0.12em', margin: '8px 0', fontFamily: 'var(--font-mono, monospace)' }}>{pair.code}</p>
          <p style={{ margin: 0, color: 'var(--muted)' }}>Works once, for {Math.round(pair.expires_in / 60)} minutes.</p>
        </div>
      )}
      {err && <p role="alert" style={{ color: 'var(--danger)' }}>{err}</p>}
      {list && list.length === 0 && <p>No devices paired yet.</p>}
      {list && list.map((d) => (
        <div className="mem row" key={d.id} style={{ justifyContent: 'space-between' }}>
          <div>
            <strong>{d.name}</strong>
            <div style={{ color: 'var(--muted)', fontSize: 13 }}>Paired {when(d.created)} · last seen {when(d.last_seen)}</div>
          </div>
          <button type="button" className="btn btn-sm" onClick={() => revoke(d)} aria-label={`Remove ${d.name}`}>Remove</button>
        </div>
      ))}
    </div>
  )
}
