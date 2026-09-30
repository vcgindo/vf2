import { useState } from 'react'
import './styles.css'
import Select, { defaultTheme } from 'react-select'

const { colors } = defaultTheme

const selectStyles = {
  control: (provided: any, state: any) => ({
    ...provided,
    minWidth: 240,
    maxWidth: 300,
    margin: 8,
    background: '#F2F2F2',
    fontSize: 16,
    outline: 'none',
    borderRadius: 6,
    border: state.isFocused ? 0 : 0,
    // This line disable the blue border
    boxShadow: state.isFocused ? 0 : 0,
    '&:hover': {
      border: state.isFocused ? 0 : 0
    }
  }),
  menu: () => ({
    boxShadow: 'inset 0 1px 0 rgba(0, 0, 0, 0.1)',
    maxWidth: 300,
    fontSize: 14
  })
}

interface SelectSearchProps {
  placeholder: string
  options: any
  valueFilter: any
  setValueFilter: any
}

const SelectSearchResetFilter = ({
  options,
  placeholder,
  valueFilter,
  setValueFilter
}: SelectSearchProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const toggleOpen = () => {
    setIsOpen(!isOpen)
  }
  const onSelectChange = (value: any) => {
    toggleOpen()
    setValueFilter(value)
  }

  return (
    <div style={{ margin: 3 }}>
      <Dropdown
        isOpen={isOpen}
        onClose={toggleOpen}
        target={
          <button className="select-search-input" onClick={toggleOpen}>
            <div className="select-Button">
              {' '}
              {valueFilter ? `${valueFilter.label}` : placeholder}
            </div>
          </button>
        }
      >
        <Select
          autoFocus
          backspaceRemovesValue={false}
          components={{ DropdownIndicator, IndicatorSeparator: null }}
          className="react-select-container"
          controlShouldRenderValue={false}
          hideSelectedOptions={false}
          isClearable={false}
          menuIsOpen
          onChange={onSelectChange}
          options={options}
          placeholder={`Search ${placeholder}`}
          styles={selectStyles}
          tabSelectsValue={false}
          value={valueFilter}
          onBlur={toggleOpen}
          theme={(theme) => ({
            ...theme,
            borderRadius: 0,
            colors: {
              ...theme.colors,
              primary25: '#F2F2F2',
              primary: '#820F4C'
            }
          })}
        />
      </Dropdown>
    </div>
  )
}

// styled components

const Menu = (props: any) => {
  const shadow = 'hsla(218, 50%, 10%, 0.1)'
  return (
    <div
      css={{
        backgroundColor: 'white',
        borderRadius: 4,
        boxShadow: `0 0 0 1px ${shadow}, 0 4px 11px ${shadow}`,
        marginTop: 8,
        position: 'absolute',
        zIndex: 2
      }}
      {...props}
    />
  )
}
const Blanket = (props: any) => (
  <div
    css={{
      bottom: 0,
      left: 0,
      top: 0,
      right: 0,
      position: 'fixed',
      zIndex: 1
    }}
    {...props}
  />
)
const Dropdown = ({ children, isOpen, target, onClose }: any) => (
  <div style={{ position: 'relative' }}>
    {target}
    {isOpen ? <Menu>{children}</Menu> : null}
    {isOpen ? <Blanket onClick={onClose} /> : null}
  </div>
)

const DropdownIndicator = () => (
  <div style={{ color: colors.neutral20, height: 24, width: 32 }}></div>
)

export default SelectSearchResetFilter
