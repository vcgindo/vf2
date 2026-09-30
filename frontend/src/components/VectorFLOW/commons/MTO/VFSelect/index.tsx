import React from 'react'
import Select from 'react-select';
import { chooseThemeColor } from '../../../../../styles/global';


const VFSelect = ({ options, themeUi, icon, placeholder,disabled, ...rest }: any) => {

    return (
        <Select
            isSearchable={true}
            isDisabled={disabled}
            components={{
                IndicatorSeparator: () => null,
                ...(icon && {DropdownIndicator: icon})
            }}
            menuPlacement={"auto"}
            // menuIsOpen={true}
            menuPortalTarget={document.body}
            styles={{
                container: (base) => ({
                    ...base,
                    width: placeholder == "Select Order Type" ? 170 : "100%"
                }),
                control: (base: any, state: any) => ({
                    ...base,
                    minHeight: "25px",
                    minWidth: "80px",
                    boxShadow: state.isFocused ? 0 : 0,
                    border: "1px solid hsl(0, 0%, 80%) !important",
                    '&:hover': {
                        border: "1px solid hsl(0, 0%, 80%)"
                    }
                }),
                menu: (base) => ({
                    ...base,
                    zIndex: "100000000",
                    minWidth: "100%",
                    width: "max-content"
                }),
                menuList: (base) => ({
                    ...base,
                    maxHeight: "120px"
                }),
                dropdownIndicator: (base) => ({
                    ...base,
                    color: "grey",
                    padding: "0"
                }),
                clearIndicator: (base) => ({
                    ...base,
                    color: "grey",
                    padding: "0"
                }),
                indicatorsContainer: (base) => ({
                    ...base,
                    padding: "0 8px"
                }),
                input: (base) => ({
                    ...base,
                    padding: "0px",
                    margin:"0px"
                })
            }}
            theme={(theme) => ({
                ...theme,
                borderRadius: 0,
                colors: {
                    ...theme.colors,
                    primary50: chooseThemeColor[themeUi]?.color4,
                    primary25: chooseThemeColor[themeUi]?.color4 + "4A",
                    primary: chooseThemeColor[themeUi]?.color4,
                },
            })}
            // menuIsOpen
            options={options}
            {...rest}

        />
    )
}

export default VFSelect