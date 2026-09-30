import { CSSProperties } from 'react'
import { SCImgOutline, SCButtonOutlineNoIcon } from './styles'
interface ButtonOutline {
  onChange: () => void
  text: string
  icon: string
  status: boolean,
  style?:CSSProperties
}

const ButtonOutlineStatus = ({
  onChange,
  text,
  icon,
  status,
  style
}: ButtonOutline) => {
  return (
    <SCButtonOutlineNoIcon status={status} onClick={onChange} style={style} data-testid='button-outline-status'>
      {icon ? <SCImgOutline src={`/assets/img/forced/${icon}.svg`} /> : ''}{' '}
      {text}
    </SCButtonOutlineNoIcon>
  )
}

export default ButtonOutlineStatus
