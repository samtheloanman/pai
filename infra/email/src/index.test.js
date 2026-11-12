import assert from 'node:assert/strict'
import { test } from 'node:test'

import { requestType } from './index.js'

test('reads the subject tag', () => {
  assert.equal(requestType('[install] llm exits 137', 'agents@freedomos.org'), 'install')
  assert.equal(requestType('  [Model] which one for 16 GB?', 'agents@freedomos.org'), 'model')
  assert.equal(requestType('Re: Fwd: [bug] vault error', 'agents@freedomos.org'), 'bug')
})

test('unknown or missing tag is general', () => {
  assert.equal(requestType('hello', 'agents@freedomos.org'), 'general')
  assert.equal(requestType('[pricing] how much', 'agents@freedomos.org'), 'general')
  assert.equal(requestType('', 'agents@freedomos.org'), 'general')
})

test('security@ always wins', () => {
  assert.equal(requestType('[docs] typo', 'security@freedomos.org'), 'security')
})
