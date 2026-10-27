import Input from '../atoms/Input.jsx'
import Label from '../atoms/Label.jsx'

/**
 * InputField — label + input avec icones de connexion.
 * Props:
 *   label      : string
 *   leftIcon   : node
 *   rightSlot  : node
 *   inputProps : props transmises a l'input
 */
export default function InputField({ label, leftIcon, rightSlot, inputProps }) {
  return (
    <div className="input-field">
      <Label>{label}</Label>
      <div className="input-field__wrap">
        {leftIcon ? <span className="input-field__icon">{leftIcon}</span> : null}
        <Input className="input-field__control" {...inputProps} />
        {rightSlot ? <span className="input-field__right">{rightSlot}</span> : null}
      </div>
    </div>
  )
}
