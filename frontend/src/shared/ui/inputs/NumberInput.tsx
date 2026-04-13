import { useState, useCallback } from 'react'
import { formatInputOnType, parseInputNumber } from '@shared/utils/format'

interface NumberInputProps {
  value: number | null
  onChange: (value: number | null) => void
  placeholder?: string
  className?: string
  disabled?: boolean
  /** Cho phép số âm */
  allowNegative?: boolean
  /** Cho phép thập phân */
  allowDecimal?: boolean
}

/**
 * NumberInput — ô nhập số tự format dấu "," nghìn khi gõ.
 *
 * STANDARDS:
 * - Dấu "," ngăn cách phần nghìn (tự thêm khi gõ)
 * - Dấu "." cho thập phân
 * - Khi blur, emit giá trị number thuần
 */
export function NumberInput({
  value,
  onChange,
  placeholder = '0',
  className = '',
  disabled = false,
  allowNegative = false,
  allowDecimal = true,
}: NumberInputProps) {
  // Display string (formatted with commas)
  const [display, setDisplay] = useState(() =>
    value != null ? formatInputOnType(String(value)) : ''
  )
  const [focused, setFocused] = useState(false)

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      let raw = e.target.value

      // Filter invalid characters
      if (!allowNegative) raw = raw.replace(/-/g, '')
      if (!allowDecimal) raw = raw.replace(/\./g, '')

      // Only allow: digits, comma, dot, minus
      raw = raw.replace(/[^0-9.,-]/g, '')

      const formatted = formatInputOnType(raw)
      setDisplay(formatted)

      // Emit parsed number
      const parsed = parseInputNumber(formatted)
      onChange(parsed)
    },
    [onChange, allowNegative, allowDecimal]
  )

  const handleFocus = useCallback(() => {
    setFocused(true)
  }, [])

  const handleBlur = useCallback(() => {
    setFocused(false)
    // Re-format cleanly on blur
    if (value != null) {
      setDisplay(formatInputOnType(String(value)))
    } else {
      setDisplay('')
    }
  }, [value])

  return (
    <input
      type="text"
      inputMode="decimal"
      value={focused ? display : value != null ? formatInputOnType(String(value)) : ''}
      onChange={handleChange}
      onFocus={handleFocus}
      onBlur={handleBlur}
      placeholder={placeholder}
      disabled={disabled}
      className={`text-right font-mono tabular-nums ${className}`}
    />
  )
}
