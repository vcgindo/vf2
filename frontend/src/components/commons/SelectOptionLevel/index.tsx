import Select from "react-select";
import { selectStyles } from "./style";
import { useUserData } from "../../../context";
import { chooseThemeColor } from "../../../styles/global";

interface SelectSearchMultipleProps {
  value: any;
  setValue: any;
  options: any;
  placeholder: string;
  isDisabled: boolean;
}

const SelectOptionLevel = ({
  value,
  setValue,
  options,
  placeholder,
  isDisabled
}: SelectSearchMultipleProps) => {  
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const handleSelect = (e: any) => {
    setValue(e);
  };

  return (
    <Select
      tabSelectsValue={false}
      hideSelectedOptions={false}
      components={{ IndicatorSeparator: null }}
      menuPosition="fixed"
      options={options}
      value={value}
      styles={selectStyles}
      placeholder={placeholder}
      isDisabled={isDisabled}
      isClearable={true}
      onChange={(e) => {
        handleSelect(e);
      }}
      theme={(theme) => ({
        ...theme,
        borderRadius: 0,
        colors: {
          ...theme.colors,
          primary25: "#F2F2F2",
          primary: chooseThemeColor[themeUi].color5,
        },
      })}
    />
  );
};

export default SelectOptionLevel;
