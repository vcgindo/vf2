import React, { InputHTMLAttributes } from 'react'
import { MTOCheckBox } from './Checkbox.styled'

interface ICheckboxProps extends InputHTMLAttributes<HTMLInputElement>{
    theme: string,
}

const Checkbox = ({theme, ...rest}: ICheckboxProps) => {
  return (
    <MTOCheckBox {...rest} theme={theme}/>
  )
}

export default Checkbox