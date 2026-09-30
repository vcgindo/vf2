import { useState, useEffect } from 'react'
import { useUserData } from "../../../context";
import './style.css'
interface CheckboxProps {
  onChange: (event: any) => void
  valueStatus: string
  name: string
}

const CheckboxPendingRequest = ({
  onChange,
  valueStatus,
  name
}: CheckboxProps) => {
  const [valueCheck, setValue] = useState(valueStatus)
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  const handleChangeInput = () => {
    setValue(valueCheck === '0' ? '1' : '0')
    onChange(name)
  }
  useEffect(() => {
    setValue(valueStatus)
  }, [valueStatus])

  return (
    <>
      <input
        className={"CheckboxPendingRequest_input " + themeUi}
        type="text"
        name={name}
        value={+valueCheck}
        disabled={!!(valueCheck !== '0' && valueCheck !== '1')}
        onClick={handleChangeInput}
        onChange={()=> {return}}
      />
    </>
  )
}

export default CheckboxPendingRequest
