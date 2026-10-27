/**
 * Button — atome de bouton reutilisable.
 * Props:
 *   variant   : 'primary' | 'secondary' | 'success' | 'danger' | 'login' | 'ghost-danger'
 *   size      : 'md' | 'sm'
 *   block     : boolean
 *   type      : type HTML du bouton
 *   icon      : node optionnel
 *   children  : contenu du bouton
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  block = false,
  type = 'button',
  icon,
  children,
  className = '',
  ...props
}) {
  const classes = [
    'button',
    `button--${variant}`,
    size === 'sm' ? 'button--sm' : '',
    block ? 'button--block' : '',
    className,
  ].filter(Boolean).join(' ')

  return (
    <button type={type} className={classes} {...props}>
      {icon}
      {children}
    </button>
  )
}
