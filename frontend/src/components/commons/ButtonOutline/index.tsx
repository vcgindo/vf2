import { SCButtonOutline, SCImgOutline } from './styles'
interface ButtonOutline {
  onChange: () => void
  text: string
  icon: string
}

const ButtonOutline = ({ onChange, text, icon }: ButtonOutline) => {
  return (
    <SCButtonOutline icons={!icon} onClick={onChange}>
      {icon ? <SCImgOutline src={`/assets/img/forced/${icon}.svg`} /> : ''}{' '}
      {text}
    </SCButtonOutline>
  )
}

export default ButtonOutline
