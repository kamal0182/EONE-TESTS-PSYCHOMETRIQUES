import { useEffect, useRef, useState } from 'react'

/**
 * DataTable - organisme de tableau generique.
 * Props:
 *   headers      : string[]
 *   rows         : [{ key, className, cells: [{ content, className }] }]
 *   emptyState   : { icon, title, text }
 *   focusRowKey  : string | number | null
 *   dateFirst    : boolean
 *   dateSecond   : boolean
 */
export default function DataTable({
  headers,
  rows,
  emptyState,
  focusRowKey = null,
  dateFirst = false,
  dateSecond = false,
}) {
  const tableRef = useRef(null)
  const [highlightedRowKey, setHighlightedRowKey] = useState(null)
  const dateColumnIndex = (dateFirst || dateSecond) ? headers.findIndex((header) => header === 'Date') : -1
  const targetDateIndex = dateFirst ? 0 : (dateSecond ? 1 : -1)
  const shouldMoveDateColumn = dateColumnIndex >= 0 && targetDateIndex >= 0 && dateColumnIndex !== targetDateIndex

  function moveItemToIndex(items, fromIndex, toIndex) {
    if (fromIndex < 0 || fromIndex >= items.length || toIndex < 0 || toIndex >= items.length || fromIndex === toIndex) {
      return items
    }
    const nextItems = [...items]
    const [movedItem] = nextItems.splice(fromIndex, 1)
    nextItems.splice(toIndex, 0, movedItem)
    return nextItems
  }

  const displayHeaders = shouldMoveDateColumn
    ? moveItemToIndex(headers, dateColumnIndex, targetDateIndex)
    : headers

  function getDisplayCells(cells) {
    if (!shouldMoveDateColumn || dateColumnIndex >= cells.length || targetDateIndex >= cells.length) {
      return cells
    }
    return moveItemToIndex(cells, dateColumnIndex, targetDateIndex)
  }

  useEffect(() => {
    if (focusRowKey === null || focusRowKey === undefined) {
      return undefined
    }

    const normalizedKey = String(focusRowKey)
    const hasMatchingRow = rows.some((row) => String(row.key) === normalizedKey)
    if (!hasMatchingRow) {
      return undefined
    }

    const rowElements = tableRef.current?.querySelectorAll('tbody tr[data-row-key]')
    if (!rowElements?.length) {
      return undefined
    }

    const targetRow = Array.from(rowElements).find(
      (rowElement) => rowElement.getAttribute('data-row-key') === normalizedKey,
    )
    if (!targetRow) {
      return undefined
    }

    targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setHighlightedRowKey(normalizedKey)

    const timeoutId = window.setTimeout(() => {
      setHighlightedRowKey((currentKey) => (currentKey === normalizedKey ? null : currentKey))
    }, 2200)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [focusRowKey, rows])

  return (
    <table ref={tableRef} className="data-table">
      <thead>
        <tr>
          {displayHeaders.map((header, index) => (
            <th key={`${header}-${index}`}>{header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {!rows.length ? (
          <tr>
            <td colSpan={displayHeaders.length}>
              <div className="empty-state">
                <div className="empty-state__icon">{emptyState.icon}</div>
                <div className="empty-state__title">{emptyState.title}</div>
                <div className="empty-state__text">{emptyState.text}</div>
              </div>
            </td>
          </tr>
        ) : (
          rows.map((row) => {
            const rowKey = String(row.key)
            const rowClassName = [
              row.className || '',
              highlightedRowKey === rowKey ? 'is-focused' : '',
            ].filter(Boolean).join(' ')
            const displayCells = getDisplayCells(row.cells)

            return (
              <tr key={row.key} className={rowClassName} data-row-key={rowKey}>
                {displayCells.map((cell, index) => (
                  <td key={`${row.key}-${index}`} className={cell.className || ''}>
                    {cell.content}
                  </td>
                ))}
              </tr>
            )
          })
        )}
      </tbody>
    </table>
  )
}
