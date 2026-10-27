import Avatar from '../atoms/Avatar.jsx'

/**
 * UserChip — avatar + textes d'identite.
 * Props:
 *   initials      : initiales affichees
 *   primaryText   : texte principal
 *   secondaryText : texte secondaire
 *   variant       : 'header' | 'sidebar'
 *   accent        : active la variante accentuee
 */
export default function UserChip({
  initials = '?',
  primaryText = '',
  secondaryText = '',
  variant = 'header',
  accent = false,
}) {
  if (variant === 'sidebar') {
    return (
      <div className="sidebar-user">
        <Avatar initials={initials} variant="sidebar" accent={accent} />
        <div>
          <div className="sidebar-user__name">{primaryText}</div>
        </div>
      </div>
    )
  }

  return (
    <div className={`user-chip${accent ? ' user-chip--accent' : ''}`}>
      <Avatar initials={initials} variant="chip" accent={accent} />
      <div>
        <div className="user-chip__name">{primaryText}</div>
        <div className={`user-chip__meta${accent ? ' user-chip__meta--accent' : ''}`}>
          {secondaryText}
        </div>
      </div>
    </div>
  )
}
