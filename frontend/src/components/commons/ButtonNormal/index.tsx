import { SCButtonNormal } from './style'

interface ButtonNormalProps {
  onChange: () => void
  text: string
  isHide: boolean
}

const ButtonNormal = ({ onChange, text, isHide }: ButtonNormalProps) => {
  return (
    <SCButtonNormal onChange={() => onChange} isHide={isHide}>
      {text.toString().replace(/,/g, ' | ')}
    </SCButtonNormal>
  )
}

export default ButtonNormal
