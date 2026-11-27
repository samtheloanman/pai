import { describe, expect, it } from 'vitest'
import { api, toRequest } from './api.js'

const msg = (role, t) => ({ role, content: [{ type: 'text', text: t }] })

describe('toRequest', () => {
  it('sends the last user message and earlier turns as history', () => {
    expect(toRequest([msg('user', 'hi'), msg('assistant', 'hello'), msg('user', 'what is on Friday?')])).toEqual({
      message: 'what is on Friday?',
      history: [{ role: 'user', content: 'hi' }, { role: 'assistant', content: 'hello' }],
    })
  })
  it('ignores non-text parts and empty turns', () => {
    const m = { role: 'user', content: [{ type: 'image', image: 'x' }, { type: 'text', text: 'look' }] }
    expect(toRequest([msg('assistant', ''), m]).message).toBe('look')
  })
  it('throws when the thread does not end with a user message', () => {
    expect(() => toRequest([msg('assistant', 'hello')])).toThrow('No user message')
    expect(() => toRequest([])).toThrow('No user message')
  })
})

describe('toRequest cloud flag', () => {
  it('omits cloud by default and sends it only when set', () => {
    expect(toRequest([msg('user', 'hi')])).not.toHaveProperty('cloud')
    expect(toRequest([msg('user', 'hi')], true).cloud).toBe(true)
    expect(toRequest([msg('user', 'hi')], false)).not.toHaveProperty('cloud')
  })
})

describe('api sign-out signal', () => {
  const run = async (path, status) => {
    const seen = []
    globalThis.window = globalThis.window || new EventTarget()
    const on = () => seen.push(1)
    window.addEventListener('pai:signed-out', on)
    globalThis.fetch = async () => ({ ok: status < 400, status, json: async () => ({ detail: 'x' }) })
    await api(path).catch(() => {})
    window.removeEventListener('pai:signed-out', on)
    return seen.length
  }
  it('fires when a data route answers 401', async () => { expect(await run('/api/memories', 401)).toBe(1) })
  it('does not fire for a wrong passphrase on the sign-in route', async () => { expect(await run('/api/auth/login', 401)).toBe(0) })
  it('does not fire on other errors', async () => { expect(await run('/api/memories', 500)).toBe(0) })
})
