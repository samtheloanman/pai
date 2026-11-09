import assert from 'node:assert/strict'
import { test } from 'node:test'

import { requestType } from './index.js'

test('reads the subject tag', () => {
  assert.equal(requestType('[install] llm exits 137', 'agents@pai.example'), 'install')
  assert.equal(requestType('  [Model] which one for 16 GB?', 'agents@pai.example'), 'model')
  assert.equal(requestType('Re: Fwd: [bug] vault error', 'agents@pai.example'), 'bug')
})

test('unknown or missing tag is general', () => {
  assert.equal(requestType('hello', 'agents@pai.example'), 'general')
  assert.equal(requestType('[pricing] how much', 'agents@pai.example'), 'general')
  assert.equal(requestType('', 'agents@pai.example'), 'general')
})

test('security@ always wins', () => {
  assert.equal(requestType('[docs] typo', 'security@pai.example'), 'security')
})
