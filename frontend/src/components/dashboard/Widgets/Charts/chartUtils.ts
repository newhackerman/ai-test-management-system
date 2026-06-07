import { ChartTheme } from './BaseChart';

// Default color schemes
export const colorSchemes = {
  default: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'],
  business: ['#1E40AF', '#0F766E', '#B45309', '#B91C1C', '#7C2D12', '#BE185D', '#0E7490', '#365314'],
  pastel: ['#93C5FD', '#6EE7B7', '#FCD34D', '#FCA5A5', '#C4B5FD', '#F9A8D4', '#67E8F9', '#BEF264'],
  vibrant: ['#2563EB', '#059669', '#D97706', '#DC2626', '#7C3AED', '#DB2777', '#0891B2', '#65A30D'],
  monochrome: ['#374151', '#6B7280', '#9CA3AF', '#D1D5DB', '#E5E7EB', '#F3F4F6', '#F9FAFB', '#FFFFFF'],
  warm: ['#DC2626', '#EA580C', '#D97706', '#CA8A04', '#65A30D', '#16A34A', '#059669', '#0D9488'],
  cool: ['#1E40AF', '#1D4ED8', '#2563EB', '#3B82F6', '#06B6D4', '#0891B2', '#0E7490', '#155E75'],
  earth: ['#92400E', '#B45309', '#D97706', '#F59E0B', '#EAB308', '#CA8A04', '#A3A3A3', '#737373']
};

// Get color scheme by name
export const getColorScheme = (schemeName: string = 'default'): string[] => {
  return colorSchemes[schemeName as keyof typeof colorSchemes] || colorSchemes.default;
};

// Generate theme-aware colors
export const getThemeColors = (theme: ChartTheme, count: number = 8): string[] => {
  const baseColors = [
    theme.primary,
    theme.secondary,
    theme.success,
    theme.warning,
    theme.error,
    theme.info
  ];

  if (count <= baseColors.length) {
    return baseColors.slice(0, count);
  }

  // Generate additional colors by varying the base colors
  const colors = [...baseColors];
  while (colors.length < count) {
    const baseColor = baseColors[colors.length % baseColors.length];
    const variation = generateColorVariation(baseColor, Math.floor(colors.length / baseColors.length));
    colors.push(variation);
  }

  return colors;
};

// Generate color variation
export const generateColorVariation = (baseColor: string, variation: number): string => {
  // Simple color variation by adjusting lightness
  const hsl = hexToHsl(baseColor);
  const lightnessDelta = (variation % 3 - 1) * 0.2; // -0.2, 0, 0.2
  const newLightness = Math.max(0.1, Math.min(0.9, hsl.l + lightnessDelta));
  
  return hslToHex(hsl.h, hsl.s, newLightness);
};

// Color utility functions
export const hexToHsl = (hex: string): { h: number; s: number; l: number } => {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }

  return { h: h * 360, s, l };
};

export const hslToHex = (h: number, s: number, l: number): string => {
  h /= 360;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h * 12) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
};

// Format numbers for display
export const formatNumber = (value: number, type: 'default' | 'percentage' | 'currency' | 'compact' = 'default'): string => {
  switch (type) {
    case 'percentage':
      return `${value.toFixed(1)}%`;
    case 'currency':
      return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;
    case 'compact':
      if (value >= 1000000) {
        return `${(value / 1000000).toFixed(1)}M`;
      } else if (value >= 1000) {
        return `${(value / 1000).toFixed(1)}K`;
      }
      return value.toString();
    default:
      return value.toLocaleString('zh-CN');
  }
};

// Format dates for charts
export const formatDate = (date: Date | string, format: 'short' | 'medium' | 'long' = 'short'): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  
  switch (format) {
    case 'long':
      return d.toLocaleDateString('zh-CN', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
    case 'medium':
      return d.toLocaleDateString('zh-CN', { 
        month: 'short', 
        day: 'numeric' 
      });
    case 'short':
    default:
      return d.toLocaleDateString('zh-CN', { 
        month: 'numeric', 
        day: 'numeric' 
      });
  }
};

// Generate sample data for charts
export const generateSampleData = (type: 'line' | 'bar' | 'pie' | 'area' | 'scatter', count: number = 10): any[] => {
  switch (type) {
    case 'line':
    case 'area':
      return Array.from({ length: count }, (_, i) => ({
        date: formatDate(new Date(Date.now() - (count - i) * 24 * 60 * 60 * 1000)),
        value: Math.floor(Math.random() * 100) + 20,
        value2: Math.floor(Math.random() * 80) + 10
      }));
      
    case 'bar':
      return Array.from({ length: count }, (_, i) => ({
        category: `类别${i + 1}`,
        value: Math.floor(Math.random() * 100) + 20,
        value2: Math.floor(Math.random() * 80) + 10
      }));
      
    case 'pie':
      return [
        { name: '已完成', value: 45 },
        { name: '进行中', value: 30 },
        { name: '待开始', value: 15 },
        { name: '已延期', value: 10 }
      ];
      
    case 'scatter':
      return Array.from({ length: count }, (_, i) => ({
        x: Math.floor(Math.random() * 100),
        y: Math.floor(Math.random() * 100),
        z: Math.floor(Math.random() * 50) + 10
      }));
      
    default:
      return [];
  }
};

// Chart interaction helpers
export const handleChartClick = (data: any, onDrillDown?: (data: any) => void) => {
  if (onDrillDown && data) {
    onDrillDown(data);
  }
};

// Export chart as image
export const exportChartAsImage = (chartRef: React.RefObject<HTMLElement>, filename: string, format: 'png' | 'svg' = 'png') => {
  if (!chartRef.current) return;

  // This would need to be implemented based on the specific chart library
  // For now, we'll use html2canvas for PNG export
  if (format === 'png') {
    import('html2canvas').then(html2canvas => {
      html2canvas.default(chartRef.current!).then(canvas => {
        const link = document.createElement('a');
        link.download = `${filename}.png`;
        link.href = canvas.toDataURL();
        link.click();
      });
    });
  }
};

// Responsive breakpoints for charts
export const getResponsiveConfig = (width: number) => {
  if (width < 480) {
    return {
      fontSize: 10,
      margin: { top: 10, right: 10, bottom: 20, left: 20 },
      showLegend: false,
      compactMode: true
    };
  } else if (width < 768) {
    return {
      fontSize: 11,
      margin: { top: 15, right: 15, bottom: 25, left: 25 },
      showLegend: true,
      compactMode: false
    };
  } else {
    return {
      fontSize: 12,
      margin: { top: 20, right: 30, bottom: 30, left: 30 },
      showLegend: true,
      compactMode: false
    };
  }
};

// Animation configurations
export const animationConfig = {
  duration: 750,
  easing: 'ease-in-out',
  delay: 0
};

// Tooltip configurations
export const tooltipConfig = {
  backgroundColor: 'rgba(255, 255, 255, 0.95)',
  border: '1px solid #e5e7eb',
  borderRadius: '6px',
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  padding: '8px 12px',
  fontSize: '12px'
};