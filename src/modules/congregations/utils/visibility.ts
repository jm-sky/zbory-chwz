import { EyeOff, Globe, LogIn, type LucideIcon, Shield } from 'lucide-vue-next'
import type { VisibilityLevel } from '../types/visibility.types'

export const VISIBILITY_ICONS: Record<VisibilityLevel, LucideIcon> = {
  hidden: EyeOff,
  public: Globe,
  authenticated: LogIn,
  pastors: Shield,
}

export function getVisibilityIcon(level: VisibilityLevel): LucideIcon {
  return VISIBILITY_ICONS[level]
}
