import React from 'react'
import Select, { components, OptionProps } from 'react-select'
import { Checkbox } from '../../../../../components';

const CustomSelect = ({ selected, placeholder, options, width, optionsWidth }: any) => {
    const Option = (props: OptionProps<any>) => {
        return (
            <components.Option {...props}>
                <div style={{ display: "flex", justifyContent: "start", alignItems: "center" }}>
                    <Checkbox name="Select" defaultChecked={props.isSelected} value="1" onChange={() => { console.log("") }} />
                    {props.data.label}
                </div>
            </components.Option>
        );
    };
    return (
        <Select
            isSearchable={false}
            components={{ Option, IndicatorSeparator: () => null }}
            value={selected}
            styles={{
                placeholder: (provided) => ({
                    ...provided,
                    color: 'black',
                    fontWeight: 500,
                    fontSize: '14px', 
                }),
                container: (base) => ({
                    ...base,
                    width: width || "max-content"
                }),
                control: (base: any, state: any) => ({
                    ...base,
                    border: "1px solid hsl(0, 0%, 80%)",
                    // This line disable the blue border
                    boxShadow: state.isFocused ? 0 : 0,
                    '&:hover': {
                        border: "1px solid hsl(0, 0%, 80%)"
                    }
                }),
                menu: (base) => ({
                    ...base,
                    width: "max-content",
                    minWidth: optionsWidth || "150px",
                    right: 0,
                }),
                option: (base) => ({
                    ...base,
                    background: "white",
                    color: "black",
                    "&:hover": {
                        background: "white"
                    }
                })
            }}
            placeholder={placeholder || ''}
            options={options || [
                { label: "M1", value: "M1" },
                { label: "M2", value: "M2" },
                { label: "M3", value: "M3" },
                { label: "M4", value: "M4" },
                { label: "M5", value: "M5" },
                { label: "M6", value: "M6" },
                { label: "M7", value: "M7" },
                { label: "M8", value: "M8" },
                { label: "M9", value: "M9" },
                { label: "M10", value: "M10" },
            ]}

        />
    )
}

export default CustomSelect