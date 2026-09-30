import React, { InputHTMLAttributes } from 'react'
import { MTORadio } from './Radio.styled'

interface IRadioProps extends InputHTMLAttributes<HTMLInputElement>{
    theme: string,
}


const Radio = ({theme, ...rest}: IRadioProps) => {
  return (
    <MTORadio theme={theme} {...rest}/>
  )
}

export default Radio