import * as React from "react"
import { cn } from "../lib/cn"

/**
 * Select primitive.
 *
 * Wraps a native <select> with consistent styling.
 */

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  isError?: boolean
  options: Array<{ value: string; label: string }>
  placeholder?: string
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ isError, options, placeholder, className, ...props }, ref) => {
    return (
      <div
        className={cn(
          "relative flex items-center w-full rounded-xl border bg-white dark:bg-zinc-900 px-3 py-2 transition-colors focus-within:ring-2",
          isError
            ? "border-danger focus-within:ring-danger/40"
            : "border-zinc-200 dark:border-zinc-800 focus-within:ring-accent/40"
        )}
      >
        <select
          ref={ref}
          className={cn(
            "w-full appearance-none bg-transparent text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none pr-6",
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {/* Chevron icon */}
        <svg
          className="absolute right-3 w-4 h-4 text-zinc-400 pointer-events-none"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
            clipRule="evenodd"
          />
        </svg>
      </div>
    )
  }
)

Select.displayName = "Select"
