import { SCButtonOutline } from './styles'
interface ButtonOutlineCheck {
  onChange: any
  text: string
  icon: string
  styles: any
}

const ButtonOutlineCheck = ({
  onChange,
  text,
  icon,
  styles
}: ButtonOutlineCheck) => {
  return (
    <SCButtonOutline
      icons={icon === 'accept'}
      style={styles}
      onClick={onChange}
    >
      {icon
        ? (
        <img
          style={{ paddingRight: 10 }}
          src={`/assets/img/check/${icon}.svg`}
        />
          )
        : (
            ''
          )}{' '}
      {text}
    </SCButtonOutline>
  )
}

export default ButtonOutlineCheck
