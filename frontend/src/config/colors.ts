export const COLORS = {
  primary: '#f59e0b',
  success: '#10b981',
  info: '#3b82f6',
  purple: '#8b5cf6',
  danger: '#ef4444',
  cyan: '#06b6d4',
  warning: '#fbbf24',
  pink: '#ec4899',
  lime: '#84cc16',
  indigo: '#6366f1',
} as const

export const CHART_COLORS = Object.values(COLORS)

export const TAG_COLORS = [
  COLORS.primary,
  COLORS.danger,
  COLORS.success,
  COLORS.info,
  COLORS.purple,
  COLORS.cyan,
  '#f97316',
  COLORS.pink,
  COLORS.lime,
  COLORS.indigo,
]
