import { useState, useEffect } from 'react'

interface CheckboxProps {
  onChange: (event: any) => void
  name: string
  value: string
  defaultChecked: boolean
}

const Checkbox = ({ onChange, name, defaultChecked }: CheckboxProps) => {
  const [checked, setChecked] = useState(defaultChecked)

  useEffect(() => {
    setChecked(defaultChecked)
  }, [defaultChecked])

  const call = () => {
    setChecked(!checked)
    onChange(event)
  }

  return (
    <>
      {/* <input className='Checkbox' type="checkbox" name={name} onClick={call} value={value} checked={checked}></input> */}
      <input
        className="CheckboxPendingRequest_input"
        type="text"
        name={name}
        onClick={call}
        value={+checked}
        checked={checked}
        onChange={() => {return}}
      />
    </>
  )
}

export default Checkbox
