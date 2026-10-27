/**
 * TableCard — carte de tableau avec actions.
 * Props:
 *   icon    : node ou string
 *   title   : string
 *   middle  : node optionnel (zone centrale du header)
 *   actions : node optionnel
 *   footer  : node optionnel sous le tableau
 *   children: contenu
 */
export default function TableCard({ icon, title, middle = null, actions, footer = null, children }) {
  return (
    <section className="table-card">
      <div className={`table-card__header${middle ? ' table-card__header--with-middle' : ''}`}>
        <div className="table-card__title">
          {icon ? <span>{icon}</span> : null}
          <span>{title}</span>
        </div>
        {middle ? <div className="table-card__header-middle">{middle}</div> : null}
        {actions ? <div className="table-card__actions">{actions}</div> : null}
      </div>
      <div className="table-card__body">{children}</div>
      {footer ? <div className="table-card__footer">{footer}</div> : null}
    </section>
  )
}
