// @ts-nocheck
// 璁捐浠ょ墝 - 鍦↗avaScript/TypeScript涓娇鐢ㄧ殑璁捐绯荤粺甯搁噺

export const colors = {
  // 涓昏壊璋?
  primary: {
    50: 'hsl(221.2 83.2% 97%)',
    100: 'hsl(221.2 83.2% 93%)',
    200: 'hsl(221.2 83.2% 85%)',
    300: 'hsl(221.2 83.2% 75%)',
    400: 'hsl(221.2 83.2% 65%)',
    500: 'hsl(221.2 83.2% 53.3%)',
    600: 'hsl(221.2 83.2% 45%)',
    700: 'hsl(221.2 83.2% 35%)',
    800: 'hsl(221.2 83.2% 25%)',
    900: 'hsl(221.2 83.2% 15%)',
    DEFAULT: 'hsl(221.2 83.2% 53.3%)',
    foreground: 'hsl(210 40% 98%)',
  },
  
  // 璇箟鑹?
  success: {
    50: 'hsl(142.1 76.2% 95%)',
    100: 'hsl(142.1 76.2% 88%)',
    500: 'hsl(142.1 76.2% 36.3%)',
    600: 'hsl(142.1 76.2% 30%)',
    700: 'hsl(142.1 76.2% 25%)',
    DEFAULT: 'hsl(142.1 76.2% 36.3%)',
    foreground: 'hsl(355.7 100% 97.3%)',
  },
  
  warning: {
    50: 'hsl(47.9 95.8% 95%)',
    100: 'hsl(47.9 95.8% 88%)',
    500: 'hsl(47.9 95.8% 53.1%)',
    600: 'hsl(47.9 95.8% 45%)',
    700: 'hsl(47.9 95.8% 35%)',
    DEFAULT: 'hsl(47.9 95.8% 53.1%)',
    foreground: 'hsl(26 83.3% 14.1%)',
  },
  
  error: {
    50: 'hsl(0 84.2% 95%)',
    100: 'hsl(0 84.2% 88%)',
    500: 'hsl(0 84.2% 60.2%)',
    600: 'hsl(0 84.2% 50%)',
    700: 'hsl(0 84.2% 40%)',
    DEFAULT: 'hsl(0 84.2% 60.2%)',
    foreground: 'hsl(210 40% 98%)',
  },
  
  info: {
    50: 'hsl(199.89 89.47% 95%)',
    100: 'hsl(199.89 89.47% 88%)',
    500: 'hsl(199.89 89.47% 49.8%)',
    600: 'hsl(199.89 89.47% 42%)',
    700: 'hsl(199.89 89.47% 35%)',
    DEFAULT: 'hsl(199.89 89.47% 49.8%)',
    foreground: 'hsl(210 40% 98%)',
  },

  // 紫色
  purple: {
    50: 'hsl(263.4 70% 95%)',
    100: 'hsl(263.4 70% 88%)',
    500: 'hsl(263.4 70% 50.4%)',
    600: 'hsl(263.4 70% 42%)',
    700: 'hsl(263.4 70% 35%)',
    DEFAULT: 'hsl(263.4 70% 50.4%)',
    foreground: 'hsl(0 0% 100%)',
  },
} as const

export const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '3rem',   // 48px
  '3xl': '4rem',   // 64px
  '4xl': '5rem',   // 80px
  '5xl': '6rem',   // 96px
} as const

export const fontSize = {
  xs: '0.75rem',    // 12px
  sm: '0.875rem',   // 14px
  base: '1rem',     // 16px
  lg: '1.125rem',   // 18px
  xl: '1.25rem',    // 20px
  '2xl': '1.5rem',  // 24px
  '3xl': '1.875rem', // 30px
  '4xl': '2.25rem', // 36px
  '5xl': '3rem',    // 48px
  '6xl': '3.75rem', // 60px
} as const

export const borderRadius = {
  sm: '0.25rem',
  md: '0.375rem',
  lg: '0.5rem',
  xl: '0.75rem',
  '2xl': '1rem',
  full: '9999px',
  DEFAULT: '0.5rem',
} as const

export const boxShadow = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
} as const

export const duration = {
  75: '75ms',
  100: '100ms',
  150: '150ms',
  200: '200ms',
  300: '300ms',
  500: '500ms',
  700: '700ms',
  1000: '1000ms',
} as const

export const easing = {
  linear: 'linear',
  in: 'cubic-bezier(0.4, 0, 1, 1)',
  out: 'cubic-bezier(0, 0, 0.2, 1)',
  inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
} as const

export const zIndex = {
  dropdown: 1000,
  sticky: 1020,
  fixed: 1030,
  modalBackdrop: 1040,
  modal: 1050,
  popover: 1060,
  tooltip: 1070,
  toast: 1080,
} as const

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const

// 宸ュ叿鍑芥暟
export const getColor = (color: string, shade?: string | number) => {
  if (!shade) return `hsl(var(--${color}))`
  return `hsl(var(--${color}-${shade}))`
}

export const getSpacing = (size: keyof typeof spacing) => {
  return `var(--spacing-${size})`
}

export const getFontSize = (size: keyof typeof fontSize) => {
  return `var(--text-${size})`
}

export const getBorderRadius = (size: keyof typeof borderRadius) => {
  return `var(--radius${size === 'DEFAULT' ? '' : `-${size}`})`
}

export const getDuration = (duration: keyof typeof duration) => {
  return `var(--duration-${duration})`
}

export const getEasing = (easing: keyof typeof easing) => {
  return `var(--ease-${easing === 'inOut' ? 'in-out' : easing})`
}

export const getZIndex = (layer: keyof typeof zIndex) => {
  return `var(--z-${layer.replace(/([A-Z])/g, '-$1').toLowerCase()})`
}

// 涓婚鐩稿叧宸ュ叿
export const createThemeVariables = (theme: 'light' | 'dark') => {
  const baseVariables = {
    '--primary': colors.primary[500],
    '--primary-foreground': colors.primary.foreground,
    '--success': colors.success[500],
    '--success-foreground': colors.success.foreground,
    '--warning': colors.warning[500],
    '--warning-foreground': colors.warning.foreground,
    '--error': colors.error[500],
    '--error-foreground': colors.error.foreground,
    '--info': colors.info[500],
    '--info-foreground': colors.info.foreground,
  }

  if (theme === 'dark') {
    return {
      ...baseVariables,
      '--background': '222.2 84% 4.9%',
      '--foreground': '210 40% 98%',
      '--muted': '217.2 32.6% 17.5%',
      '--muted-foreground': '215 20.2% 65.1%',
      '--border': '217.2 32.6% 17.5%',
      '--card': '222.2 84% 4.9%',
      '--card-foreground': '210 40% 98%',
    }
  }

  return {
    ...baseVariables,
    '--background': '0 0% 100%',
    '--foreground': '222.2 84% 4.9%',
    '--muted': '210 40% 96%',
    '--muted-foreground': '215.4 16.3% 46.9%',
    '--border': '214.3 31.8% 91.4%',
    '--card': '0 0% 100%',
    '--card-foreground': '222.2 84% 4.9%',
  }
}