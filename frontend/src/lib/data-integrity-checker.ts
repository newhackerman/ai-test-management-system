export interface IntegrityCheckResult {
  entityType: string
  entityId: number | string
  status: 'valid' | 'invalid' | 'missing' | 'corrupted'
  issues: string[]
  localChecksum?: string
  remoteChecksum?: string
  lastChecked: string
}

export interface IntegrityReport {
  totalChecked: number
  validCount: number
  invalidCount: number
  missingCount: number
  corruptedCount: number
  results: IntegrityCheckResult[]
  generatedAt: string
}

export class DataIntegrityChecker {
  private checksumCache = new Map<string, string>()

  calculateChecksum(data: unknown): string {
    const normalized = JSON.stringify(this.normalize(data))
    const cached = this.checksumCache.get(normalized)
    if (cached) return cached

    let hash = 0
    for (let index = 0; index < normalized.length; index += 1) {
      hash = ((hash << 5) - hash + normalized.charCodeAt(index)) | 0
    }
    const checksum = Math.abs(hash).toString(36)
    this.checksumCache.set(normalized, checksum)
    return checksum
  }

  async checkEntityIntegrity(
    entityType: string,
    entityId: number | string,
    localData?: unknown,
    remoteData?: unknown,
  ): Promise<IntegrityCheckResult> {
    const result: IntegrityCheckResult = {
      entityType,
      entityId,
      status: 'valid',
      issues: [],
      lastChecked: new Date().toISOString(),
    }

    if (localData == null && remoteData == null) {
      return { ...result, status: 'missing', issues: ['本地和远端数据均不存在'] }
    }
    if (localData == null) {
      return { ...result, status: 'missing', issues: ['本地数据缺失'] }
    }
    if (remoteData == null) {
      return { ...result, status: 'missing', issues: ['远端数据缺失'] }
    }

    const localChecksum = this.calculateChecksum(localData)
    const remoteChecksum = this.calculateChecksum(remoteData)
    if (localChecksum !== remoteChecksum) {
      return {
        ...result,
        status: 'invalid',
        issues: this.compareObjects(localData, remoteData),
        localChecksum,
        remoteChecksum,
      }
    }

    return { ...result, localChecksum, remoteChecksum }
  }

  async generateReport(items: Array<{
    entityType: string
    entityId: number | string
    localData?: unknown
    remoteData?: unknown
  }>): Promise<IntegrityReport> {
    const results = await Promise.all(
      items.map((item) => this.checkEntityIntegrity(item.entityType, item.entityId, item.localData, item.remoteData)),
    )

    return {
      totalChecked: results.length,
      validCount: results.filter((item) => item.status === 'valid').length,
      invalidCount: results.filter((item) => item.status === 'invalid').length,
      missingCount: results.filter((item) => item.status === 'missing').length,
      corruptedCount: results.filter((item) => item.status === 'corrupted').length,
      results,
      generatedAt: new Date().toISOString(),
    }
  }

  clearCache() {
    this.checksumCache.clear()
  }

  private normalize(data: unknown): unknown {
    if (Array.isArray(data)) return data.map((item) => this.normalize(item))
    if (!data || typeof data !== 'object') return data

    return Object.fromEntries(
      Object.entries(data as Record<string, unknown>)
        .filter(([key]) => !['created_at', 'updated_at', 'version', '_syncing', '_lastSynced', '_localChanges'].includes(key))
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, value]) => [key, this.normalize(value)]),
    )
  }

  private compareObjects(localData: unknown, remoteData: unknown): string[] {
    const issues: string[] = []
    const local = this.normalize(localData) as Record<string, unknown>
    const remote = this.normalize(remoteData) as Record<string, unknown>
    const keys = new Set([...Object.keys(local || {}), ...Object.keys(remote || {})])

    keys.forEach((key) => {
      if (JSON.stringify(local?.[key]) !== JSON.stringify(remote?.[key])) {
        issues.push(`字段 ${key} 不一致`)
      }
    })

    return issues.length > 0 ? issues : ['数据校验和不一致']
  }
}

export const dataIntegrityChecker = new DataIntegrityChecker()
export default dataIntegrityChecker
