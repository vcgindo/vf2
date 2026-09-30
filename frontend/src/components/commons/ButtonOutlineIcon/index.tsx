import { SCButtonOutlineIcon, SCImg } from './style'
import { useUserData } from "../../../context";

interface ButtonOutlineIconProps {
  onClick?: () => void
  text: string
  icon: string
  disabled:boolean
}

const ButtonOutlineIcon = ({ onClick, text, icon,disabled }: ButtonOutlineIconProps) => {
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  return (
    <>
      <SCButtonOutlineIcon onClick={onClick} themeUi={themeUi} disabled={disabled}>
        {icon ? <SCImg src={icon} /> : ''}
        {text.toString().replace(',', ' | ')}
      </SCButtonOutlineIcon>
    </>
  )
}

export default ButtonOutlineIcon
