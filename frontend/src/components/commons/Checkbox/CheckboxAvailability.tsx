import { useState, useEffect } from 'react'

interface CheckboxProps {
  onChange: (event: any) => void
  name: string
  value: string
  defaultChecked: boolean
}

const CheckboxAvailability = ({
  onChange,
  name,
  defaultChecked
}: CheckboxProps) => {
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
      <input
        className="CheckboxAvailability_input"
        type="text"
        name={name}
        onClick={call}
        value={+checked}
        checked={checked}
      />
    </>
  )
}

export default CheckboxAvailability
