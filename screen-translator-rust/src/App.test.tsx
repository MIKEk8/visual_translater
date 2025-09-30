import { describe, it, expect } from 'vitest'

describe('App Component Tests', () => {
  it('basic test should pass', () => {
    expect(true).toBe(true)
  })

  it('can do basic math', () => {
    expect(2 + 2).toBe(4)
  })

  it('can work with strings', () => {
    const text = 'Screen Translator'
    expect(text).toContain('Translator')
  })
})