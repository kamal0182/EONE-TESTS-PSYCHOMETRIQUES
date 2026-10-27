/**
 * AuthLayout — template structurel de la page d'authentification.
 * Props:
 *   children : contenu reel injecte par la page
 */
export default function AuthLayout({ children }) {
  return (
    <div className="auth-page">
      <div className="top-accent" />
      <div className="auth-main">
        <div className="auth-panel">
          {children || (
            <div className="auth-placeholder" aria-hidden="true">
              <strong>Placeholder Auth</strong>
              <span className="auth-placeholder-line" />
              <span className="auth-placeholder-line" />
              <span className="auth-placeholder-line" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
