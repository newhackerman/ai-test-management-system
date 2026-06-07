import { apiService } from '@/services/api-service';

export interface ColorScheme {
  id: string;
  name: string;
  type: 'system' | 'enterprise' | 'custom';
  category: string;
  colors: string[];
  description?: string;
  isDefault?: boolean;
  isActive?: boolean;
  rating?: number;
  usageCount?: number;
  previewImage?: string;
  createdBy?: number;
  organizationId?: number;
  isPublic?: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface UserColorPreference {
  id: number;
  userId: number;
  colorSchemeId?: string;
  customColors?: string[];
  autoSwitchDarkMode: boolean;
  accessibilityMode: boolean;
  highContrast: boolean;
  applyToCharts: boolean;
  applyToWidgets: boolean;
  applyToTheme: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CreateColorSchemeRequest {
  name: string;
  category?: string;
  colors: string[];
  description?: string;
  isPublic?: boolean;
}

export interface ColorSchemePreview {
  colorPalette: string[];
  previewImage: string;
  accessibility: {
    minContrast: number;
    warnings: string[];
    recommendations: string[];
  };
  analysis: {
    dominantHue: string;
    brightnessRange: { min: number; max: number };
    saturationRange: { min: number; max: number };
    colorHarmony: string;
    temperature: 'warm' | 'cool' | 'neutral';
  };
  recommendations: string[];
}

class ColorSchemeService {
  private baseUrl = '/api/v1/dashboards/color-schemes';

  /**
   * Get available color schemes for the current user
   */
  async getColorSchemes(
    schemeType?: string,
    category?: string
  ): Promise<ColorScheme[]> {
    try {
      const params = new URLSearchParams();
      if (schemeType) params.append('scheme_type', schemeType);
      if (category) params.append('category', category);

      const response = await apiService.get(`${this.baseUrl}?${params}`) as { data: ColorScheme[] };
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '获取配色方案失败');
    }
  }

  /**
   * Create a custom color scheme
   */
  async createColorScheme(request: CreateColorSchemeRequest): Promise<ColorScheme> {
    try {
      const response = await apiService.post(this.baseUrl, request) as { data: ColorScheme };
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '创建配色方案失败');
    }
  }

  /**
   * Apply a color scheme to the current user
   */
  async applyColorScheme(
    schemeId: string,
    options: {
      applyToCharts?: boolean;
      applyToWidgets?: boolean;
      applyToTheme?: boolean;
    } = {}
  ): Promise<void> {
    try {
      await apiService.post(`${this.baseUrl}/${schemeId}/apply`, {
        apply_to_charts: options.applyToCharts ?? true,
        apply_to_widgets: options.applyToWidgets ?? true,
        apply_to_theme: options.applyToTheme ?? false
      });
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '应用配色方案失败');
    }
  }

  /**
   * Get user's color preferences
   */
  async getUserPreferences(): Promise<UserColorPreference | null> {
    try {
      const response = await apiService.get(`${this.baseUrl}/preferences`) as { data: UserColorPreference };
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null; // No preferences set yet
      }
      throw new Error(error.response?.data?.detail || '获取用户配色偏好失败');
    }
  }

  /**
   * Update user's color preferences
   */
  async updateUserPreferences(
    preferences: Partial<UserColorPreference>
  ): Promise<UserColorPreference> {
    try {
      const response = await apiService.put(`${this.baseUrl}/preferences`, preferences) as { data: UserColorPreference };
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '更新用户配色偏好失败');
    }
  }

  /**
   * Preview a color scheme
   */
  async previewColorScheme(colors: string[]): Promise<ColorSchemePreview> {
    try {
      const response = await apiService.post(`${this.baseUrl}/preview`, {
        color_palette: colors
      }) as { data: ColorSchemePreview };
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '预览配色方案失败');
    }
  }

  /**
   * Get effective colors for the current user
   */
  async getEffectiveColors(): Promise<string[]> {
    try {
      const response = await apiService.get(`${this.baseUrl}/effective-colors`) as { data: { colors: string[] } };
      return response.data.colors || this.getDefaultColors();
    } catch (error: any) {
      console.warn('Failed to get effective colors, using default:', error.message);
      return this.getDefaultColors();
    }
  }

  /**
   * Share a color scheme (make it public)
   */
  async shareColorScheme(schemeId: string, makePublic: boolean = true): Promise<void> {
    try {
      await apiService.post(`${this.baseUrl}/${schemeId}/share`, {
        make_public: makePublic
      });
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '分享配色方案失败');
    }
  }

  /**
   * Rate a color scheme
   */
  async rateColorScheme(schemeId: string, rating: number): Promise<void> {
    try {
      if (rating < 0 || rating > 5) {
        throw new Error('评分必须在0-5之间');
      }
      
      await apiService.post(`${this.baseUrl}/${schemeId}/rate`, {
        rating
      });
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '评价配色方案失败');
    }
  }

  /**
   * Delete a custom color scheme
   */
  async deleteColorScheme(schemeId: string): Promise<void> {
    try {
      await apiService.delete(`${this.baseUrl}/${schemeId}`);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '删除配色方案失败');
    }
  }

  /**
   * Export a color scheme to JSON
   */
  exportColorScheme(scheme: ColorScheme): void {
    try {
      const exportData = {
        name: scheme.name,
        type: scheme.type,
        category: scheme.category,
        colors: scheme.colors,
        description: scheme.description,
        exportedAt: new Date().toISOString()
      };

      const dataStr = JSON.stringify(exportData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `${scheme.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}-color-scheme.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      URL.revokeObjectURL(url);
    } catch (error) {
      throw new Error('导出配色方案失败');
    }
  }

  /**
   * Import a color scheme from JSON file
   */
  async importColorScheme(file: File): Promise<ColorScheme> {
    try {
      const text = await file.text();
      const importData = JSON.parse(text);
      
      // Validate imported data
      if (!importData.name || !importData.colors || !Array.isArray(importData.colors)) {
        throw new Error('无效的配色方案文件格式');
      }

      // Create the imported scheme
      const createRequest: CreateColorSchemeRequest = {
        name: `${importData.name} (导入)`,
        category: importData.category || '自定义',
        colors: importData.colors,
        description: importData.description || '从文件导入的配色方案',
        isPublic: false
      };

      return await this.createColorScheme(createRequest);
    } catch (error: any) {
      if (error instanceof SyntaxError) {
        throw new Error('配色方案文件格式错误');
      }
      throw new Error(error.message || '导入配色方案失败');
    }
  }

  /**
   * Copy colors to clipboard
   */
  async copyColorsToClipboard(colors: string[]): Promise<void> {
    try {
      const colorString = colors.join(', ');
      await navigator.clipboard.writeText(colorString);
    } catch (error) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = colors.join(', ');
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  }

  /**
   * Validate color format
   */
  validateColorFormat(color: string): boolean {
    // Check HEX format
    const hexRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
    if (hexRegex.test(color)) return true;

    // Check RGB format
    const rgbRegex = /^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/;
    if (rgbRegex.test(color)) return true;

    // Check RGBA format
    const rgbaRegex = /^rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(0|1|0?\.\d+)\s*\)$/;
    if (rgbaRegex.test(color)) return true;

    return false;
  }

  /**
   * Convert color to HEX format
   */
  convertToHex(color: string): string {
    if (color.startsWith('#')) return color;

    // Handle RGB/RGBA
    const rgbMatch = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (rgbMatch) {
      const r = parseInt(rgbMatch[1]);
      const g = parseInt(rgbMatch[2]);
      const b = parseInt(rgbMatch[3]);
      
      return '#' + [r, g, b].map(x => {
        const hex = x.toString(16);
        return hex.length === 1 ? '0' + hex : hex;
      }).join('');
    }

    return color;
  }

  /**
   * Get default color palette
   */
  private getDefaultColors(): string[] {
    return [
      '#3B82F6', // Blue
      '#10B981', // Green
      '#F59E0B', // Yellow
      '#EF4444', // Red
      '#8B5CF6', // Purple
      '#EC4899', // Pink
      '#06B6D4', // Cyan
      '#84CC16'  // Lime
    ];
  }

  /**
   * Get system predefined color schemes
   */
  getSystemColorSchemes(): ColorScheme[] {
    return [
      {
        id: 'default',
        name: '默认方案',
        type: 'system',
        category: '通用',
        colors: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'],
        description: '系统默认配色方案，适用于大多数场景',
        isDefault: true,
        isActive: true,
        rating: 4.5,
        usageCount: 1250
      },
      {
        id: 'business-blue',
        name: '蓝色商务',
        type: 'system',
        category: '商务',
        colors: ['#1E40AF', '#3B82F6', '#60A5FA', '#93C5FD', '#DBEAFE', '#1F2937', '#374151', '#6B7280'],
        description: '专业的蓝色系配色，适合商务报告和企业应用',
        rating: 4.3,
        usageCount: 890
      },
      {
        id: 'nature-green',
        name: '绿色生态',
        type: 'system',
        category: '环保',
        colors: ['#059669', '#10B981', '#34D399', '#6EE7B7', '#A7F3D0', '#064E3B', '#065F46', '#047857'],
        description: '清新的绿色系配色，适合环保和健康主题',
        rating: 4.2,
        usageCount: 567
      },
      {
        id: 'tech-purple',
        name: '紫色科技',
        type: 'system',
        category: '科技',
        colors: ['#7C3AED', '#8B5CF6', '#A78BFA', '#C4B5FD', '#DDD6FE', '#581C87', '#6B21A8', '#7C2D92'],
        description: '现代感十足的紫色系配色，适合科技和创新主题',
        rating: 4.4,
        usageCount: 723
      },
      {
        id: 'warm-orange',
        name: '橙色活力',
        type: 'system',
        category: '活跃',
        colors: ['#EA580C', '#F97316', '#FB923C', '#FDBA74', '#FED7AA', '#9A3412', '#C2410C', '#DC2626'],
        description: '充满活力的橙色系配色，适合展示活跃数据',
        rating: 4.1,
        usageCount: 445
      },
      {
        id: 'alert-red',
        name: '红色警示',
        type: 'system',
        category: '警示',
        colors: ['#DC2626', '#EF4444', '#F87171', '#FCA5A5', '#FECACA', '#7F1D1D', '#991B1B', '#B91C1C'],
        description: '醒目的红色系配色，适合风险监控和警告提示',
        rating: 4.0,
        usageCount: 334
      },
      {
        id: 'cool-cyan',
        name: '青色清新',
        type: 'system',
        category: '清新',
        colors: ['#0891B2', '#06B6D4', '#22D3EE', '#67E8F9', '#A5F3FC', '#164E63', '#155E75', '#0E7490'],
        description: '清新的青色系配色，适合清新风格的界面',
        rating: 4.2,
        usageCount: 612
      },
      {
        id: 'geek-multi',
        name: '极客风格',
        type: 'system',
        category: '开发者',
        colors: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'],
        description: '多彩对比的配色方案，适合开发者和技术展示',
        rating: 4.6,
        usageCount: 892
      }
    ];
  }
}

export const colorSchemeService = new ColorSchemeService();