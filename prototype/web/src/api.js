// Plain fetch helpers for the PAI backend plus the adapter that feeds assistant-ui.
export const api = async (path, opts = {}) => {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts })
  const body = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(body.detail || `Request failed (${r.status})`)
  return body
}

const text = (m) => m.content.filter((p) => p.type === 'text').map((p) => p.text).join('')

/** Split assistant-ui's thread into the last user message and the prior turns the backend expects. */
export function toRequest(messages, cloud = false) {
  const turns = messages.map((m) => ({ role: m.role, content: text(m) })).filter((m) => m.content)
  const last = turns.pop()
  if (!last || last.role !== 'user') throw new Error('No user message to send')
  return { message: last.content, history: turns, ...(cloud ? { cloud: true } : {}) }
}

export const paiAdapter = {
  async run({ messages, abortSignal, cloud }) {
    const { reply } = await api('/api/chat', { method: 'POST', body: JSON.stringify(toRequest(messages, cloud)), signal: abortSignal })
    return { content: [{ type: 'text', text: reply }] }
  },
}
