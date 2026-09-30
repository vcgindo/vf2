import React from 'react'
import Select, { components, OptionProps } from 'react-select';
import Radio from '../Radio';

const RadioSelect = ({options ,theme, color="white", Icon, ...rest}: any) => {
    const Option = (props: OptionProps<any>) => {
        return (
            <components.Option {...props}>
                <div style={{ display: "flex", justifyContent: "start", alignItems: "center", textAlign:"left", fontSize:"12px", gap:"5px" }}>
                    <Radio theme={theme} defaultChecked={props.isSelected}/>
                    {props.label}
                    {Icon && <Icon props={props}/>}
                </div>
            </components.Option>
        );
    }
  return (
        <Select
            isSearchable={false}
            components={{ Option, IndicatorSeparator: () => null }}
            menuPlacement={"auto"}
            menuPosition={"fixed"}
            // menuIsOpen={true}
            styles={{
                container: (base) => ({
                    ...base,
                    width: "max-content"
                }),
                control: (base: any, state: any) => ({
                    ...base,
                    background: color,
                    borderRadius:0,
                    border: "1px solid hsl(0, 0%, 80%)",
                    // This line disable the blue border
                    boxShadow: state.isFocused ? 0 : 0,
                    minHeight:"25px",
                    minWidth:"80px",
                    '&:hover': {
                        border: "1px solid hsl(0, 0%, 80%)"
                    }
                }),
                menu: (base) => ({
                    ...base,
                    zIndex:"100000000",
                    minWidth:"100%",
                    width:"max-content"
                }),
                menuList: (base) => ({
                  ...base,
                  maxHeight:"120px"  
                }),
                option: (base) => ({
                    ...base,
                    background: "white",
                    color: "black",
                    padding:"8px",
                    "&:hover": {
                        background: "white"
                    }
                }),
                dropdownIndicator:(base) => ({
                    ...base,
                    color: "grey",
                    padding: "0"
                }),
                clearIndicator: (base) => ({
                    ...base,
                    color: "grey",
                    padding: "0"
                }),
                indicatorsContainer:(base) => ({
                    ...base,
                    padding: "0 8px"
                })
            }}
            // menuIsOpen
            placeholder={""}
            options={options}
            {...rest}

        />
  )
}

export default RadioSelect