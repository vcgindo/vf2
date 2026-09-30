import './styles.css'
import { useState } from 'react'
import { useUserData } from "../../../context";

interface ButtonSwitchProps {
  onClick: any
  labelOn: string
  labelOff: string
  toggled: boolean
}

const ButtonOutlineAvailability = ({
  labelOn,
  labelOff,
  toggled,
  onClick
}: ButtonSwitchProps) => {
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [isToggled, toggle] = useState(toggled)
  const callback = () => {
    toggle(!isToggled)
    onClick(!isToggled)
  }
  return (
    <div className={`button-switch-availability ${themeUi}`}>
      <input
        type="checkbox"
        id="switch-orange"
        defaultChecked={isToggled}
        onClick={callback}
        className={`switch ${themeUi}`}
      />
      <label className={`lbl-off ${themeUi}`}>{labelOff}</label>
      <label className={`lbl-on ${themeUi}`}>{labelOn}</label>
    </div>
  )
}

export default ButtonOutlineAvailability
