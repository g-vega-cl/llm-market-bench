import { clsx, type ClassValue } from "clsx"

/**
 * Conditional className utility.
 * Replaces tailwind-merge since Tailwind v4 handles duplicate class resolution natively.
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}
