import { SCSelectOption, SCSelectIcon, SCSelectBox } from './styles'

interface SelectOptionProps {
  name: string
  handleChange: (e: any) => void
  value: any
  items: any[]
  icon: string
}
const SelectInput = ({
  name,
  value,
  handleChange,
  items,
  icon
}: SelectOptionProps) => {
  return (
    <SCSelectOption>
      {icon ? <SCSelectIcon src={`/assets/img/ist/${icon}.svg`} /> : ''}
      <SCSelectBox
        icons={icon === 'target'}
        icon={!icon}
        name={name}
        value={value}
        onChange={handleChange}
      >
        {items &&
          items.map((item: any) => (
            <option
              style={{ color: 'black', width: 20 }}
              key={JSON.stringify(item)}
              value={item}
            >
              {`${item}ㅤ`}
            </option>
          ))}
      </SCSelectBox>
    </SCSelectOption>
  )
}

export default SelectInput
