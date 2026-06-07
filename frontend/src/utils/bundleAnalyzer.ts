export interface BundleAnalysis {
  totalSize: number
  gzippedSize: number
  chunks: ChunkInfo[]
  dependencies: DependencyInfo[]
  recommendations: OptimizationRecommendation[]
  treeshaking: TreeshakingInfo
  duplicates: DuplicateInfo[]
}

export interface ChunkInfo {
  name: string
  size: number
  gzippedSize: number
  modules: ModuleInfo[]
  loadTime: number
  isAsync: boolean
  parents: string[]
  children: string[]
}

export interface ModuleInfo {
  name: string
  size: number
  reasons: string[]
  isEntry: boolean
  isExternal: boolean
  chunks: string[]
}

export interface DependencyInfo {
  name: string
  version: string
  size: number
  gzippedSize: number
  isDevDependency: boolean
  usageCount: number
  alternatives: string[]
}

export interface OptimizationRecommendation {
  type: 'size' | 'performance' | 'dependency' | 'treeshaking'
  severity: 'low' | 'medium' | 'high'
  title: string
  description: string
  impact: string
  solution: string
  estimatedSavings?: number
}

export interface TreeshakingInfo {
  unusedExports: string[]
  sideEffects: string[]
  potentialSavings: number
}

export interface DuplicateInfo {
  module: string
  chunks: string[]
  size: number
  instances: number
}

export class BundleAnalyzer {
  private analysisCache = new Map<string, BundleAnalysis>()

  async analyzeBundles(bundleStats: any = {}, packageJson: any = {}): Promise<BundleAnalysis> {
    const cacheKey = JSON.stringify({
      chunks: bundleStats?.chunks?.length || 0,
      assets: bundleStats?.assets?.length || 0,
      deps: Object.keys(packageJson?.dependencies || {}).length,
    })

    const cached = this.analysisCache.get(cacheKey)
    if (cached) return cached

    const chunks = this.analyzeChunks(bundleStats)
    const dependencies = this.analyzeDependencies(bundleStats, packageJson)
    const duplicates = this.findDuplicates(bundleStats)
    const treeshaking = this.analyzeTreeshaking(bundleStats)
    const totalSize = chunks.reduce((sum, chunk) => sum + chunk.size, 0)
    const gzippedSize = chunks.reduce((sum, chunk) => sum + chunk.gzippedSize, 0)
    const recommendations = this.generateRecommendations({
      chunks,
      dependencies,
      duplicates,
      treeshaking,
      totalSize,
      gzippedSize,
    })

    const analysis: BundleAnalysis = {
      totalSize,
      gzippedSize,
      chunks,
      dependencies,
      recommendations,
      treeshaking,
      duplicates,
    }
    this.analysisCache.set(cacheKey, analysis)
    return analysis
  }

  generateOptimizationReport(analysis: BundleAnalysis): string {
    const lines = [
      '# Bundle 优化报告',
      '',
      `总大小：${this.formatBytes(analysis.totalSize)}`,
      `Gzip 估算：${this.formatBytes(analysis.gzippedSize)}`,
      `Chunk 数量：${analysis.chunks.length}`,
      '',
      '## 优化建议',
    ]

    if (analysis.recommendations.length === 0) {
      lines.push('暂无明显优化项。')
    } else {
      analysis.recommendations.forEach((item, index) => {
        lines.push(`${index + 1}. [${item.severity}] ${item.title} - ${item.solution}`)
      })
    }

    return lines.join('\n')
  }

  private analyzeChunks(bundleStats: any): ChunkInfo[] {
    const chunks = Array.isArray(bundleStats?.chunks) ? bundleStats.chunks : []
    const assets = Array.isArray(bundleStats?.assets) ? bundleStats.assets : []

    if (chunks.length === 0 && assets.length > 0) {
      return assets.map((asset: any) => this.createChunk(asset.name, asset.size, [], false))
    }

    return chunks.map((chunk: any) =>
      this.createChunk(
        chunk.names?.[0] || chunk.name || String(chunk.id ?? 'chunk'),
        chunk.size || 0,
        this.analyzeModules(chunk.modules || []),
        !chunk.initial,
        chunk.parents || [],
        chunk.children || [],
      ),
    )
  }

  private createChunk(
    name: string,
    size: number,
    modules: ModuleInfo[],
    isAsync: boolean,
    parents: string[] = [],
    children: string[] = [],
  ): ChunkInfo {
    return {
      name,
      size,
      gzippedSize: this.estimateGzippedSize(size),
      modules,
      loadTime: this.estimateLoadTime(size),
      isAsync,
      parents,
      children,
    }
  }

  private analyzeModules(modules: any[]): ModuleInfo[] {
    return modules.map((module) => ({
      name: module.name || module.identifier || 'unknown',
      size: module.size || 0,
      reasons: (module.reasons || []).map((reason: any) => reason.moduleName || reason.userRequest || 'unknown'),
      isEntry: Boolean(module.isEntry || module.issuerName === null),
      isExternal: /node_modules/.test(module.name || module.identifier || ''),
      chunks: module.chunks || [],
    }))
  }

  private analyzeDependencies(bundleStats: any, packageJson: any): DependencyInfo[] {
    const dependencyVersions = {
      ...(packageJson?.dependencies || {}),
      ...(packageJson?.devDependencies || {}),
    }
    const modules = this.analyzeChunks(bundleStats).flatMap((chunk) => chunk.modules)

    return Object.entries(dependencyVersions).map(([name, version]) => {
      const usage = modules.filter((module) => module.name.includes(`node_modules/${name}`) || module.name.includes(`node_modules\\${name}`))
      const size = usage.reduce((sum, module) => sum + module.size, 0)
      return {
        name,
        version: String(version),
        size,
        gzippedSize: this.estimateGzippedSize(size),
        isDevDependency: Boolean(packageJson?.devDependencies?.[name]),
        usageCount: usage.length,
        alternatives: [],
      }
    })
  }

  private analyzeTreeshaking(bundleStats: any): TreeshakingInfo {
    const modules = this.analyzeChunks(bundleStats).flatMap((chunk) => chunk.modules)
    const unusedExports = modules.filter((module) => module.size === 0).map((module) => module.name)
    return {
      unusedExports,
      sideEffects: [],
      potentialSavings: unusedExports.length * 1024,
    }
  }

  private findDuplicates(bundleStats: any): DuplicateInfo[] {
    const modules = this.analyzeChunks(bundleStats).flatMap((chunk) =>
      chunk.modules.map((module) => ({ ...module, chunkName: chunk.name })),
    )
    const grouped = new Map<string, Array<ModuleInfo & { chunkName: string }>>()
    modules.forEach((module) => {
      const key = module.name.replace(/[?#].*$/, '')
      grouped.set(key, [...(grouped.get(key) || []), module])
    })

    return Array.from(grouped.entries())
      .filter(([, items]) => new Set(items.map((item) => item.chunkName)).size > 1)
      .map(([module, items]) => ({
        module,
        chunks: Array.from(new Set(items.map((item) => item.chunkName))),
        size: Math.max(...items.map((item) => item.size), 0),
        instances: items.length,
      }))
  }

  private generateRecommendations(input: {
    chunks: ChunkInfo[]
    dependencies: DependencyInfo[]
    duplicates: DuplicateInfo[]
    treeshaking: TreeshakingInfo
    totalSize: number
    gzippedSize: number
  }): OptimizationRecommendation[] {
    const recommendations: OptimizationRecommendation[] = []

    input.chunks
      .filter((chunk) => chunk.size > 500 * 1024)
      .forEach((chunk) => {
        recommendations.push({
          type: 'size',
          severity: chunk.size > 1024 * 1024 ? 'high' : 'medium',
          title: `${chunk.name} 体积偏大`,
          description: `当前 chunk 大小为 ${this.formatBytes(chunk.size)}。`,
          impact: '首屏或路由切换加载时间可能增加。',
          solution: '拆分懒加载模块或配置 manualChunks。',
          estimatedSavings: Math.round(chunk.size * 0.25),
        })
      })

    if (input.duplicates.length > 0) {
      recommendations.push({
        type: 'dependency',
        severity: 'medium',
        title: '存在重复模块',
        description: `检测到 ${input.duplicates.length} 个重复模块。`,
        impact: '重复代码会增加包体积。',
        solution: '检查依赖版本和 chunk 拆分策略。',
      })
    }

    if (input.treeshaking.potentialSavings > 0) {
      recommendations.push({
        type: 'treeshaking',
        severity: 'low',
        title: '可继续优化 Tree Shaking',
        description: '检测到潜在未使用导出。',
        impact: '可能存在少量无效代码。',
        solution: '改用按需导入并确认第三方包 sideEffects 配置。',
        estimatedSavings: input.treeshaking.potentialSavings,
      })
    }

    return recommendations
  }

  private estimateGzippedSize(size: number): number {
    return Math.round(size * 0.32)
  }

  private estimateLoadTime(size: number): number {
    const bytesPerSecond = 125 * 1024
    return Number((size / bytesPerSecond).toFixed(2))
  }

  private formatBytes(bytes: number): string {
    if (!bytes) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
    return `${(bytes / 1024 ** exponent).toFixed(2)} ${units[exponent]}`
  }
}

export const bundleAnalyzer = new BundleAnalyzer()

export function analyzeBundles(bundleStats: any, packageJson?: any) {
  return bundleAnalyzer.analyzeBundles(bundleStats, packageJson)
}

export function generateOptimizationReport(analysis: BundleAnalysis) {
  return bundleAnalyzer.generateOptimizationReport(analysis)
}

export default bundleAnalyzer
