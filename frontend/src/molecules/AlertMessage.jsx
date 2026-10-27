import Icon from '../atoms/Icon.jsx'

/**
 * AlertMessage — message d'erreur ou de succes.
 * Props:
 *   message : string
 *   type    : 'error' | 'success'
 */
export default function AlertMessage({ message, type = 'error' }) {
  if (!message) return null

  return (
    <div className={`alert alert--${type}`}>
      <Icon name="emoji" emoji={type === 'error' ? '⚠️' : type === 'warning' ? '📧' : '✅'} />
      <span>{message}</span>
    </div>
  )
}
