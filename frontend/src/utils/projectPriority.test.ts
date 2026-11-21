import { describe, expect, it } from 'vitest'

import {
  getProjectPriorityBadgeClass,
  getProjectPriorityLabel,
  projectPriorityOptions,
} from '@/utils/projectPriority'

describe('projectPriority', () => {
  it('labels every priority in Chinese', () => {
    expect(getProjectPriorityLabel('LOW')).toBe('低')
    expect(getProjectPriorityLabel('MEDIUM')).toBe('中')
    expect(getProjectPriorityLabel('HIGH')).toBe('高')
    expect(getProjectPriorityLabel('URGENT')).toBe('紧急')
  })

  it('falls back for missing or unknown priorities', () => {
    expect(getProjectPriorityLabel(undefined)).toBe('-')
    expect(getProjectPriorityLabel('')).toBe('-')
    expect(getProjectPriorityLabel('UNKNOWN')).toBe('UNKNOWN')
  })

  it('gives URGENT a distinct deep-red badge', () => {
    const urgent = getProjectPriorityBadgeClass('URGENT')
    expect(urgent).toContain('bg-red-100')
    expect(urgent).toContain('text-red-800')
    expect(urgent).not.toBe(getProjectPriorityBadgeClass('HIGH'))
  })

  it('colours each level differently', () => {
    expect(getProjectPriorityBadgeClass('HIGH')).toContain('orange')
    expect(getProjectPriorityBadgeClass('MEDIUM')).toContain('amber')
    expect(getProjectPriorityBadgeClass('LOW')).toContain('green')
  })

  it('returns an empty class for missing or unknown priorities', () => {
    expect(getProjectPriorityBadgeClass(undefined)).toBe('')
    expect(getProjectPriorityBadgeClass('')).toBe('')
    expect(getProjectPriorityBadgeClass('UNKNOWN')).toBe('')
  })

  it('lists the four priorities low to urgent', () => {
    expect(projectPriorityOptions.map((o) => o.value)).toEqual([
      'LOW',
      'MEDIUM',
      'HIGH',
      'URGENT',
    ])
  })
})
