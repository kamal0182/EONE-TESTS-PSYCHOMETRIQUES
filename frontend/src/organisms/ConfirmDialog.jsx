import Button from '../atoms/Button.jsx'
import Icon from '../atoms/Icon.jsx'

export default function ConfirmDialog({
  title,
  message,
  onCancel,
  onConfirm,
  isLoading = false,
  confirmLabel = 'Continuer',
  confirmLoadingLabel = 'Suppression...',
  confirmVariant = 'danger',
}) {
  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal__header">
          <h2 className="modal__title">{title}</h2>
          <button type="button" className="icon-button" onClick={onCancel} aria-label="Fermer">
            <Icon name="close" />
          </button>
        </div>

        <div className="modal__body" style={{ padding: '24px', textAlign: 'center' }}>
          <p style={{ fontSize: '1rem', lineHeight: '1.5', color: '#333' }}>
            {message}
          </p>
        </div>

        <div className="modal__footer">
          <Button variant="secondary" onClick={onCancel} disabled={isLoading}>
            Annuler
          </Button>
          <Button variant={confirmVariant} onClick={onConfirm} disabled={isLoading}>
            {isLoading ? confirmLoadingLabel : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
