import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * shadcn/ui class-name helper.
 * Combines `clsx` for conditional classes with `tailwind-merge` so that
 * conflicting utility classes (e.g. `px-2` vs `px-4`) are resolved to the last one.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
