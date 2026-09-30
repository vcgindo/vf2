import { useState } from 'react'
import Select, { defaultTheme, components } from 'react-select'
import { selectStyles, styleMoreSelect } from './style'
import { useTranslation } from 'react-i18next'
import { useUserData } from "../../../context";
import { chooseThemeColor } from "../../../styles/global";

const { colors } = defaultTheme
interface SelectSearchMultipleProps {
  value: any
  setValue: any
  options: any
  placeholder: string
}

const SelectSearchMultiple = ({
  value,
  setValue,
  options,
  placeholder
}: SelectSearchMultipleProps) => {
  const { t } = useTranslation()
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [isOpen, setIsOpen] = useState(false)

  const toggleOpen = () => {
    setIsOpen(!isOpen)
  }

  const handleSelect = (e: any) => {
    setValue(e)
  }

  return (
    <div style={{ margin: 3 }}>
      <Dropdown
        isOpen={isOpen}
        onClose={toggleOpen}
        target={
          <button className="select-search-input" onClick={toggleOpen}>
            <div className="select-Button">
              {value.length > 0
                ? `${value[0]?.label}${value.length > 1 ? '...' : ''}`
                : placeholder}
            </div>
          </button>
        }
      >
        <Select
          autoFocus
          closeMenuOnSelect={false}
          components={{
            DropdownIndicator,
            IndicatorSeparator: null,
            MultiValue
          }}
          className="react-select-container"
          value={value}
          isMulti
          menuIsOpen
          options={options}
          onChange={(e) => {
            handleSelect(e)
          }}
          placeholder={t('filter.select.title')}
          styles={selectStyles}
          tabSelectsValue={false}
          onBlur={toggleOpen}
          hideSelectedOptions={false}
          theme={(theme) => ({
            ...theme,
            borderRadius: 0,
            colors: {
              ...theme.colors,
              primary25: '#F2F2F2',
              primary: chooseThemeColor[themeUi].color5
            }
          })}
        />
      </Dropdown>
    </div>
  )
}

const Dropdown = ({ children, isOpen, target, onClose }: any) => (
  <div style={{ position: 'relative' }}>
    {target}
    {isOpen ? <Menu>{children}</Menu> : null}
    {isOpen ? <Blanket onClick={onClose} /> : null}
  </div>
)

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

const DropdownIndicator = () => (
  <div style={{ color: colors.neutral20, height: 24, width: 32 }}></div>
)

const MultiValue = ({ index, getValue, ...props }: any) => {
  const maxToShow = 1
  const overflow = getValue()
    .slice(maxToShow)
    .map((x: any) => x.label)

  return index < maxToShow
    ? (
    <components.MultiValue {...props} />
      )
    : index === maxToShow
      ? (
    <MoreSelectedBadge items={overflow} />
        )
      : null
}

const MoreSelectedBadge = ({ items }: any) => {
  const { t } = useTranslation()
  const title = items.join(', ')
  const length = items.length
  const label = `+${length} ${t('filter.select.more')}`

  return (
    <div style={styleMoreSelect} title={title}>
      {label}
    </div>
  )
}

export default SelectSearchMultiple
