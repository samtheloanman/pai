import { describe, expect, it } from 'vitest'
import { activityLine, riskLabel } from './format.js'

const e = (kind, fields = {}) => ({ id: 1, ts: '2026-11-01T10:00:00.000Z', kind, fields })
const M = 'gen_ai.request.model'

describe('activityLine', () => {
  it('model call with tokens', () => {
    expect(activityLine(e('model_call', { [M]: 'pai-chat', 'gen_ai.usage.input_tokens': 200, 'gen_ai.usage.output_tokens': 1112 }))).toBe('Model call · pai-chat · 1,312 tokens')
  })
  it('model call without tokens', () => expect(activityLine(e('model_call', { [M]: 'pai-chat' }))).toBe('Model call · pai-chat'))
  it('failed model call', () => expect(activityLine(e('model_call', { [M]: 'pai-chat', error: 'HTTP 502' }))).toBe('Model call failed · pai-chat'))
  it('route', () => expect(activityLine(e('route', { 'pai.route': 'local-fast', tier: 1 }))).toBe('Routed to local-fast (tier 1)'))
  it('outbound with separators', () => expect(activityLine(e('outbound', { 'pai.provider': 'openrouter', chars: 1204 }))).toBe('Sent to openrouter · 1,204 chars'))
  it('simple kinds', () => {
    expect(activityLine(e('action_proposed'))).toBe('Approval requested')
    expect(activityLine(e('action_confirmed'))).toBe('Approved')
    expect(activityLine(e('action_rejected'))).toBe('Rejected')
    expect(activityLine(e('memory_added'))).toBe('Memory added')
    expect(activityLine(e('memory_deleted'))).toBe('Memory deleted')
  })
  it('config change', () => expect(activityLine(e('config_changed', { what: 'rules' }))).toBe('Settings changed · rules'))
  it('unknown kind', () => expect(activityLine(e('some_new_kind'))).toBe('Some new kind'))
})

describe('riskLabel', () => {
  it('maps each risky kind', () => {
    expect(riskLabel('send')).toBe('Sends')
    expect(riskLabel('delete')).toBe('Deletes')
    expect(riskLabel('spend')).toBe('Spends')
    expect(riskLabel('system')).toBe('Changes system')
  })
})
