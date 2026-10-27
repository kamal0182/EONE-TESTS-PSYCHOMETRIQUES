/**
 * Avatar — atome d'avatar textuel.
 * Props:
 *   initials : texte affiche
 *   variant  : 'chip' | 'sidebar'
 *   accent   : applique la variante accentuee
 */
export default function Avatar({ initials = '?', variant = 'chip', accent = false }) {
  return (
    <div className={`avatar avatar--${variant}${accent ? ' avatar--accent' : ''}`}>
      {initials}
    </div>
  )
}
