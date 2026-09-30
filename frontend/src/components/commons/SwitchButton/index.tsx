import './styles.css'
import { useState } from 'react'

interface ButtonSwitchProps {
  onClick: any
  labelOn: string
  labelOff: string
  toggled: boolean
}

const ButtonOutline = ({
  labelOn,
  labelOff,
  toggled,
  onClick
}: ButtonSwitchProps) => {
  const [isToggled, toggle] = useState(toggled)
  const callback = () => {
    toggle(!isToggled)
    onClick(!isToggled)
  }
  return (
    <div className="button-switch">
      <input
        type="checkbox"
        id="switch-orange"
        defaultChecked={isToggled}
        onClick={callback}
        className="switch"
      />
      <label className="lbl-off">{labelOff}</label>
      <label className="lbl-on">{labelOn}</label>
    </div>
  )
}

export default ButtonOutline
