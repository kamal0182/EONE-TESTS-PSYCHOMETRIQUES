/**
 * Select — atome de liste deroulante.
 * Props: toutes les props d'un <select>.
 */
export default function Select({ className = '', children, ...props }) {
  return (
    <select className={`select-base ${className}`.trim()} {...props}>
      {children}
    </select>
  )
}
