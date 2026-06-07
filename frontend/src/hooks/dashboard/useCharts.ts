import { useState, useEffect, useCallback, useMemo } from 'react';
import { ChartTheme } from '@/components/dashboard/Widgets/Charts/BaseChart';
import { getColorScheme, colorSchemes } from '@/components/dashboard/Widgets/Charts/chartUtils';
import { useAuth } from '@/stores/auth';

export interface ChartPreferences {
  colorScheme: string;
  theme: ChartTheme;
  animation: boolean;
  showGrid: boolean;
  showLegend: boolean;
}

const defaultLightTheme: ChartTheme = {
  primary: '#3B82F6',
  secondary: '#10B981',
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#06B6D4',
  background: '#FFFFFF',
  surface: '#F8FAFC',
  text: '#1F2937',
  textSecondary: '#6B7280',
  border: '#E5E7EB',
  grid: '#F3F4F6'
};

const defaultDarkTheme: ChartTheme = {
  primary: '#60A5FA',
  secondary: '#34D399',
  success: '#4ADE80',
  warning: '#FBBF24',
  error: '#F87171',
  info: '#22D3EE',
  background: '#1F2937',
  surface: '#374151',
  text: '#F9FAFB',
  textSecondary: '#D1D5DB',
  border: '#4B5563',
  grid: '#374151'
};

export const useCharts = () => {
  const { user } = useAuth();
  const [preferences, setPreferences] = useState<ChartPreferences>({
    colorScheme: 'default',
    theme: defaultLightTheme,
    animation: true,
    showGrid: true,
    showLegend: true
  });
  const [isDarkMode, setIsDarkMode] = useState(false);

  // Load user preferences from localStorage
  useEffect(() => {
    const savedPreferences = localStorage.getItem(`chart-preferences-${user?.id || 'default'}`);
    if (savedPreferences) {
      try {
        const parsed = JSON.parse(savedPreferences);
        setPreferences(prev => ({ ...prev, ...parsed }));
      } catch (error) {
        console.error('Failed to parse chart preferences:', error);
      }
    }

    // Detect system dark mode
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    setIsDarkMode(mediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setIsDarkMode(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [user?.id]);

  // Save preferences to localStorage
  const savePreferences = useCallback((newPreferences: Partial<ChartPreferences>) => {
    const updated = { ...preferences, ...newPreferences };
    setPreferences(updated);
    localStorage.setItem(`chart-preferences-${user?.id || 'default'}`, JSON.stringify(updated));
  }, [preferences, user?.id]);

  // Get current theme based on dark mode
  const currentTheme = useMemo(() => {
    const baseTheme = isDarkMode ? defaultDarkTheme : defaultLightTheme;
    return { ...baseTheme, ...preferences.theme };
  }, [isDarkMode, preferences.theme]);

  // Get current color scheme
  const currentColorScheme = useMemo(() => {
    return getColorScheme(preferences.colorScheme);
  }, [preferences.colorScheme]);

  // Available color schemes
  const availableColorSchemes = useMemo(() => {
    return Object.keys(colorSchemes).map(key => ({
      id: key,
      name: getColorSchemeName(key),
      colors: colorSchemes[key as keyof typeof colorSchemes]
    }));
  }, []);

  // Update color scheme
  const setColorScheme = useCallback((scheme: string) => {
    savePreferences({ colorScheme: scheme });
  }, [savePreferences]);

  // Update theme
  const setTheme = useCallback((theme: Partial<ChartTheme>) => {
    savePreferences({ theme: { ...currentTheme, ...theme } });
  }, [currentTheme, savePreferences]);

  // Toggle animation
  const toggleAnimation = useCallback(() => {
    savePreferences({ animation: !preferences.animation });
  }, [preferences.animation, savePreferences]);

  // Toggle grid
  const toggleGrid = useCallback(() => {
    savePreferences({ showGrid: !preferences.showGrid });
  }, [preferences.showGrid, savePreferences]);

  // Toggle legend
  const toggleLegend = useCallback(() => {
    savePreferences({ showLegend: !preferences.showLegend });
  }, [preferences.showLegend, savePreferences]);

  // Reset to defaults
  const resetPreferences = useCallback(() => {
    const defaultPrefs: ChartPreferences = {
      colorScheme: 'default',
      theme: isDarkMode ? defaultDarkTheme : defaultLightTheme,
      animation: true,
      showGrid: true,
      showLegend: true
    };
    setPreferences(defaultPrefs);
    localStorage.removeItem(`chart-preferences-${user?.id || 'default'}`);
  }, [isDarkMode, user?.id]);

  // Export chart as image
  const exportChart = useCallback(async (
    chartRef: React.RefObject<HTMLElement>,
    filename: string,
    format: 'png' | 'svg' | 'pdf' = 'png'
  ) => {
    if (!chartRef.current) {
      throw new Error('Chart reference not found');
    }

    try {
      if (format === 'png') {
        const html2canvas = await import('html2canvas');
        const canvas = await html2canvas.default(chartRef.current, {
          backgroundColor: currentTheme.background,
          scale: 2, // Higher resolution
          useCORS: true
        });
        
        const link = document.createElement('a');
        link.download = `${filename}.png`;
        link.href = canvas.toDataURL();
        link.click();
      } else if (format === 'svg') {
        // SVG export would need additional implementation
        throw new Error('SVG export not yet implemented');
      } else if (format === 'pdf') {
        // PDF export would need additional implementation
        throw new Error('PDF export not yet implemented');
      }
    } catch (error) {
      console.error('Failed to export chart:', error);
      throw error;
    }
  }, [currentTheme.background]);

  // Get chart config with current preferences
  const getChartConfig = useCallback((baseConfig: any = {}) => {
    return {
      ...baseConfig,
      colorScheme: currentColorScheme,
      theme: currentTheme,
      animation: preferences.animation,
      showGrid: preferences.showGrid,
      showLegend: preferences.showLegend
    };
  }, [currentColorScheme, currentTheme, preferences]);

  return {
    preferences,
    currentTheme,
    currentColorScheme,
    availableColorSchemes,
    isDarkMode,
    setColorScheme,
    setTheme,
    toggleAnimation,
    toggleGrid,
    toggleLegend,
    resetPreferences,
    exportChart,
    getChartConfig,
    savePreferences
  };
};

// Helper function to get color scheme display name
function getColorSchemeName(key: string): string {
  const names: { [key: string]: string } = {
    default: '默认',
    business: '商务',
    pastel: '柔和',
    vibrant: '鲜艳',
    monochrome: '单色',
    warm: '暖色',
    cool: '冷色',
    earth: '大地'
  };
  return names[key] || key;
}

export default useCharts;