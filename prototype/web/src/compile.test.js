import { describe, expect, it, vi } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { api } from './api.js'

describe('Panels.jsx onboarding compile hooks (source verification)', () => {
  const panelsPath = path.resolve(__dirname, 'Panels.jsx')
  const content = fs.readFileSync(panelsPath, 'utf8')

  it('triggers /api/onboarding/compile in Setup after rules draft', () => {
    // Look for draft function calling compile
    expect(content).toMatch(/api\(['"]\/api\/rules\/draft['"],\s*\{\s*method:\s*['"]POST['"]\s*\}\)[\s\S]*?api\(['"]\/api\/onboarding\/compile['"],\s*\{\s*method:\s*['"]POST['"]\s*\}\)/)
  })

  it('triggers /api/onboarding/compile in Setup after fallback rules PUT', () => {
    // Look for fallback PUT /api/rules calling compile
    expect(content).toMatch(/api\(['"]\/api\/rules['"],\s*\{\s*method:\s*['"]PUT['"],\s*body:[\s\S]*?\}\)[\s\S]*?api\(['"]\/api\/onboarding\/compile['"],\s*\{\s*method:\s*['"]POST['"]\s*\}\)/)
  })

  it('triggers /api/onboarding/compile in Rules after saving rules', () => {
    // In Rules component, save() must call PUT /api/rules followed by POST /api/onboarding/compile
    const rulesSection = content.slice(content.indexOf('export function Rules'))
    expect(rulesSection).toMatch(/api\(['"]\/api\/rules['"],\s*\{\s*method:\s*['"]PUT['"],\s*body:\s*JSON\.stringify\(\{\s*text\s*\}\)\s*\}\)[\s\S]*?api\(['"]\/api\/onboarding\/compile['"],\s*\{\s*method:\s*['"]POST['"]\s*\}\)/)
  })
})

describe('api /api/onboarding/compile client behavior', () => {
  it('posts to /api/onboarding/compile and returns compiled persona', async () => {
    const mockResponse = {
      ok: true,
      persona_id: 'pai-default',
      system_prompt: 'You are sovereign assistant PAI...',
      skills_enabled: ['memory-vault'],
      onboarding_profile_count: 8,
    }

    const originalFetch = global.fetch
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    })

    try {
      const res = await api('/api/onboarding/compile', { method: 'POST' })
      expect(global.fetch).toHaveBeenCalledWith('/api/onboarding/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      expect(res.ok).toBe(true)
      expect(res.persona_id).toBe('pai-default')
      expect(res.onboarding_profile_count).toBe(8)
    } finally {
      global.fetch = originalFetch
    }
  })

  it('propagates HTTP 400 error message when interview is incomplete', async () => {
    const originalFetch = global.fetch
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'finish the interview first' }),
    })

    try {
      await expect(api('/api/onboarding/compile', { method: 'POST' })).rejects.toThrow('finish the interview first')
    } finally {
      global.fetch = originalFetch
    }
  })
})
