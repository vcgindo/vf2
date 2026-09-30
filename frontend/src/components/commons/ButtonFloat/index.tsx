import { SCButtonFloat, SCImg } from './style'
import { useUserData } from "../../../context";

interface ButtonFloatProps {
  onClick: any
  text: string
  icon: string
  styles?: React.CSSProperties
  iconStyles?: React.CSSProperties
}

const ButtonFloat = ({ onClick, text, icon, styles,iconStyles }: ButtonFloatProps) => {
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  return (
    <>
      <SCButtonFloat onClick={onClick} themeUi={themeUi} style={styles}>
        {icon && <SCImg src={icon} style={iconStyles} /> }
        {text && text.toString().replace(',', ' | ')}
      </SCButtonFloat>
    </>
  )
}

export default ButtonFloat
