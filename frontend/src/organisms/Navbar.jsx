/**
 * Navbar — organisme de structure d'entete.
 * (Copie d'ENOSISAPP sans la cloche de notifications : pas de service de notifications ici.)
 * Props:
 *   brand            : contenu gauche
 *   children         : contenu droit
 *   mobileMenuButton : bouton hamburger optionnel (visible en mobile)
 */
export default function Navbar({ brand, children, mobileMenuButton = null }) {
  return (
    <header className="app-header">
      {mobileMenuButton}
      <div className="app-logo">
        {brand}
      </div>

      <div className="header-right">
        {children}
      </div>
    </header>
  )
}
