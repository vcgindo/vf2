import './styles.css'
import { useState } from 'react'
interface ButtonCheckProps {
  onClick: any
  text: string
  toggled: boolean
}
const ButtonCheck = ({ onClick, text, toggled }: ButtonCheckProps) => {
  const [isToggled, toggle] = useState(toggled)
  const callback = () => {
    toggle(!isToggled)
    onClick(!isToggled)
  }
  return (
    <>
      <input
        className="checkbox_ist"
        type="checkbox"
        defaultChecked={isToggled}
        id="Checkbox"
        name="Checkbox"
      />
      <label onClick={callback}>
        <span className="label-name" style={isToggled ? { color: '#000' } : {}}>
          {text}
        </span>
      </label>
    </>
  )
}

export default ButtonCheck
