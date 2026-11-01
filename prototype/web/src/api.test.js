import { describe, expect, it } from 'vitest'
import { toRequest } from './api.js'

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
