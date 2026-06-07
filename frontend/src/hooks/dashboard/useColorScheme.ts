import { useState, useEffect, useCallback } from 'react';
import { colorSchemeService, ColorScheme, UserColorPreference, CreateColorSchemeRequest, ColorSchemePreview } from '@/services/dashboard/colorSchemeService';
import { toast } from 'react-hot-toast';

export const useColorScheme = () => {
  const [colorSchemes, setColorSchemes] = useState<ColorScheme[]>([]);
  const [userPreferences, setUserPreferences] = useState<UserColorPreference | null>(null);
  const [effectiveColors, setEffectiveColors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<ColorSchemePreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Load color schemes
  const loadColorSchemes = useCallback(async (schemeType?: string, category?: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const schemes = await colorSchemeService.getColorSchemes(schemeType, category);
      setColorSchemes(schemes);
    } catch (err: any) {
      setError(err.message || '加载配色方案失败');
      toast.error('加载配色方案失败');
      
      // Fallback to system schemes if API fails
      const systemSchemes = colorSchemeService.getSystemColorSchemes();
      setColorSchemes(systemSchemes);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load user preferences
  const loadUserPreferences = useCallback(async () => {
    try {
      const preferences = await colorSchemeService.getUserPreferences();
      setUserPreferences(preferences);
    } catch (err: any) {
      console.warn('Failed to load user preferences:', err.message);
      // Don't show error toast for preferences as it's not critical
    }
  }, []);

  // Load effective colors
  const loadEffectiveColors = useCallback(async () => {
    try {
      const colors = await colorSchemeService.getEffectiveColors();
      setEffectiveColors(colors);
    } catch (err: any) {
      console.warn('Failed to load effective colors:', err.message);
      // Use default colors as fallback
      setEffectiveColors(colorSchemeService.getSystemColorSchemes()[0].colors);
    }
  }, []);

  // Apply color scheme
  const applyColorScheme = useCallback(async (
    schemeId: string,
    options: {
      applyToCharts?: boolean;
      applyToWidgets?: boolean;
      applyToTheme?: boolean;
    } = {}
  ) => {
    try {
      await colorSchemeService.applyColorScheme(schemeId, options);
      toast.success('配色方案应用成功');
      
      // Reload preferences and effective colors
      await Promise.all([
        loadUserPreferences(),
        loadEffectiveColors()
      ]);
      
      return true;
    } catch (err: any) {
      setError(err.message || '应用配色方案失败');
      toast.error('应用配色方案失败');
      return false;
    }
  }, [loadUserPreferences, loadEffectiveColors]);

  // Create custom color scheme
  const createColorScheme = useCallback(async (request: CreateColorSchemeRequest) => {
    try {
      const newScheme = await colorSchemeService.createColorScheme(request);
      toast.success('自定义配色方案创建成功');
      
      // Reload color schemes
      await loadColorSchemes();
      
      return newScheme;
    } catch (err: any) {
      setError(err.message || '创建配色方案失败');
      toast.error('创建配色方案失败');
      throw err;
    }
  }, [loadColorSchemes]);

  // Preview color scheme
  const previewColorScheme = useCallback(async (colors: string[]) => {
    try {
      setPreviewLoading(true);
      const preview = await colorSchemeService.previewColorScheme(colors);
      setPreviewData(preview);
      return preview;
    } catch (err: any) {
      setError(err.message || '预览配色方案失败');
      toast.error('预览配色方案失败');
      throw err;
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  // Update user preferences
  const updateUserPreferences = useCallback(async (preferences: Partial<UserColorPreference>) => {
    try {
      const updated = await colorSchemeService.updateUserPreferences(preferences);
      setUserPreferences(updated);
      toast.success('配色偏好更新成功');
      
      // Reload effective colors if color scheme changed
      if (preferences.colorSchemeId !== undefined) {
        await loadEffectiveColors();
      }
      
      return updated;
    } catch (err: any) {
      setError(err.message || '更新配色偏好失败');
      toast.error('更新配色偏好失败');
      throw err;
    }
  }, [loadEffectiveColors]);

  // Share color scheme
  const shareColorScheme = useCallback(async (schemeId: string, makePublic: boolean = true) => {
    try {
      await colorSchemeService.shareColorScheme(schemeId, makePublic);
      toast.success(makePublic ? '配色方案已设为公开' : '配色方案已设为私有');
      
      // Reload color schemes to reflect changes
      await loadColorSchemes();
      
      return true;
    } catch (err: any) {
      setError(err.message || '分享配色方案失败');
      toast.error('分享配色方案失败');
      return false;
    }
  }, [loadColorSchemes]);

  // Rate color scheme
  const rateColorScheme = useCallback(async (schemeId: string, rating: number) => {
    try {
      await colorSchemeService.rateColorScheme(schemeId, rating);
      toast.success('评价提交成功');
      
      // Reload color schemes to reflect updated rating
      await loadColorSchemes();
      
      return true;
    } catch (err: any) {
      setError(err.message || '评价配色方案失败');
      toast.error('评价配色方案失败');
      return false;
    }
  }, [loadColorSchemes]);

  // Delete color scheme
  const deleteColorScheme = useCallback(async (schemeId: string) => {
    try {
      await colorSchemeService.deleteColorScheme(schemeId);
      toast.success('配色方案删除成功');
      
      // Reload color schemes
      await loadColorSchemes();
      
      return true;
    } catch (err: any) {
      setError(err.message || '删除配色方案失败');
      toast.error('删除配色方案失败');
      return false;
    }
  }, [loadColorSchemes]);

  // Export color scheme
  const exportColorScheme = useCallback((scheme: ColorScheme) => {
    try {
      colorSchemeService.exportColorScheme(scheme);
      toast.success('配色方案导出成功');
    } catch (err: any) {
      toast.error('导出配色方案失败');
    }
  }, []);

  // Import color scheme
  const importColorScheme = useCallback(async (file: File) => {
    try {
      const importedScheme = await colorSchemeService.importColorScheme(file);
      toast.success('配色方案导入成功');
      
      // Reload color schemes
      await loadColorSchemes();
      
      return importedScheme;
    } catch (err: any) {
      setError(err.message || '导入配色方案失败');
      toast.error('导入配色方案失败');
      throw err;
    }
  }, [loadColorSchemes]);

  // Copy colors to clipboard
  const copyColorsToClipboard = useCallback(async (colors: string[]) => {
    try {
      await colorSchemeService.copyColorsToClipboard(colors);
      toast.success('颜色代码已复制到剪贴板');
    } catch (err: any) {
      toast.error('复制颜色代码失败');
    }
  }, []);

  // Validate color format
  const validateColorFormat = useCallback((color: string) => {
    return colorSchemeService.validateColorFormat(color);
  }, []);

  // Convert color to HEX
  const convertToHex = useCallback((color: string) => {
    return colorSchemeService.convertToHex(color);
  }, []);

  // Get current active scheme
  const getCurrentScheme = useCallback(() => {
    if (!userPreferences?.colorSchemeId) return null;
    return colorSchemes.find(scheme => scheme.id === userPreferences.colorSchemeId) || null;
  }, [colorSchemes, userPreferences]);

  // Filter schemes by type and category
  const filterSchemes = useCallback((type?: string, category?: string) => {
    return colorSchemes.filter(scheme => {
      if (type && scheme.type !== type) return false;
      if (category && scheme.category !== category) return false;
      return true;
    });
  }, [colorSchemes]);

  // Get scheme categories
  const getCategories = useCallback(() => {
    const categories = new Set(colorSchemes.map(scheme => scheme.category));
    return Array.from(categories).sort();
  }, [colorSchemes]);

  // Initialize data
  useEffect(() => {
    const initializeData = async () => {
      await Promise.all([
        loadColorSchemes(),
        loadUserPreferences(),
        loadEffectiveColors()
      ]);
    };

    initializeData();
  }, [loadColorSchemes, loadUserPreferences, loadEffectiveColors]);

  return {
    // Data
    colorSchemes,
    userPreferences,
    effectiveColors,
    previewData,
    loading,
    previewLoading,
    error,

    // Actions
    loadColorSchemes,
    applyColorScheme,
    createColorScheme,
    previewColorScheme,
    updateUserPreferences,
    shareColorScheme,
    rateColorScheme,
    deleteColorScheme,
    exportColorScheme,
    importColorScheme,
    copyColorsToClipboard,

    // Utilities
    validateColorFormat,
    convertToHex,
    getCurrentScheme,
    filterSchemes,
    getCategories,

    // Refresh
    refresh: () => Promise.all([
      loadColorSchemes(),
      loadUserPreferences(),
      loadEffectiveColors()
    ])
  };
};