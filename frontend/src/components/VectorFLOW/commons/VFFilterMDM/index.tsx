import { VFFilterDustbinIcon, VFFilterInputField, VFFilterSeperator, VFFilterWrapper } from "./styles";
import Select from 'react-select'
import {type Option, type Filter} from '../../../../VectorFlow/types/MDM';
import { useDispatch, useSelector } from 'react-redux';
import { UPDATE_FILTER_VALUE } from "../../../../redux/actions/MDM";
import { useUserData } from "../../../../context";
import { useCallback, useMemo, useState } from 'react';
import type { RootState } from '../../../../redux/store/store';
import { operatorDataTypeMapper } from "../../../../helpers/MtoMDMConstants";
import { Field } from "../../../../VectorFlow/types/MDM";
export interface VFFilterProps{
    onDelete:()=>void
    fields:Option[]
    operators:Option[]
    currFilter:Filter
    filters:Filter[],
    isDisabled:boolean
}

export interface CustomSelectProps{
    width:string
    placeholder:string
    onChange:(...params:any)=>void
    options:any[]
    value:any,
    isDisabled:boolean
}

export interface CustomInputProps{
    value:string
    onChange:(e:any)=>void
    disabled?: boolean
    type?:string
}

const VFFilter = (props:VFFilterProps)=>{
    const dispatch = useDispatch();
    const{
        fields,
        operators,
        onDelete,
        currFilter,
        isDisabled
    } = props
    
    
    const activeMaster = useSelector((state: RootState) => state.mdm.activeMaster);
    const [fieldDataType, setFieldDataType] = useState("");
    
    // Memoizing validOperators using useMemo to avoid frequent recalculations
    //update operator based on dataType
    const validOperators = useMemo(() => {
        return operators.filter(operator =>
            operatorDataTypeMapper[fieldDataType]?.includes(operator.value)
        );
    }, [fieldDataType, operators]);

    //update field data type based on selected main filter type
    const updateFieldDataType = useCallback((fieldKey: string) => {
        const selectedField = activeMaster.fields.find((field: Field) => field.key === fieldKey);
        if (selectedField) {
            setFieldDataType(selectedField.dataType);
        }
    }, [activeMaster.fields]);

    //Update field data type, update active master filter in redux
    const handleOnChange = useCallback((value: string, property: string) => {
        if (property === 'field') {
            updateFieldDataType(value);
        }
        dispatch(UPDATE_FILTER_VALUE({ value, property, filterId: currFilter.id }));
    }, [dispatch, updateFieldDataType, currFilter.id]);


    return(
        <VFFilterWrapper data-testid="vffilter-wrapper">
            <CustomSelect 
                width="588px" 
                placeholder="Select" 
                onChange={(e:any)=>handleOnChange(e.value,'field')} 
                options={fields}
                value={fields.find((field)=>field.value === currFilter.field)}
                isDisabled={isDisabled}
            />
            <VFFilterSeperator/>
            <CustomSelect 
                width="298px" 
                placeholder="Select" 
                onChange={(e:any)=>handleOnChange(e.value,'operator')} 
                options={validOperators}
                value={validOperators.find((field) => field.value === currFilter.operator) ?? ""}
                isDisabled={isDisabled}
            />
            <VFFilterSeperator/>
            <CustomInput
                value={currFilter.text} 
                onChange={(e:any)=>handleOnChange(e.target.value,'text')}
                disabled={isDisabled || fieldDataType === ""}
                type={fieldDataType}
            />
            <VFFilterSeperator/>
            <VFFilterDustbinIcon 
                src="/assets/img/VectorFLOW/NMS/dustbin.svg" 
                onClick={onDelete}
                data-testid='delete-icon'
            />
        </VFFilterWrapper>
    )
}



const CustomSelect = (props:CustomSelectProps)=>{

    const {
        placeholder,
        onChange,
        options,
        value,
        isDisabled
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    return (
        <Select
            styles={{
                option: (baseStyles, { isSelected }) => ({
                    ...baseStyles,
                    backgroundColor: isSelected ? themeUi==="REGALBLAZE"?"#FCA311":"#BC3D80" : "white",
                   
                   
                    "&:hover": {
                        backgroundColor:themeUi==="REGALBLAZE"?"rgb(252, 163, 17,0.3)": '#bc3d814d',
                        color:"black",
                    }
                }),
                container:(styles)=>({
                    ...styles,
                    width:'100%'
                }),
                control:(styles, { isFocused })=>({
                    ...styles,
                    // borderColor: isFocused ? "none": "hsl(0, 0%, 80%);",

                    height:'37px',
                    width:'100%',
                    background:' #FFFFFF ',
                    fontSize:'13px',
                    border:'none',
                    borderRadius:'6px',
                    paddingLeft:'8px',
                    borderColor: isFocused ? "none": "hsl(0, 0%, 80%);",
                    // border: "none",
                    // borderBottom: error ? "3px solid #D03E3E;" : menuIsOpen || isFocused ? '3px solid #820F4C' : '3px solid #A1A1A1',
                    boxShadow: 'none',
                    "&:hover":{
                        borderColor: isFocused ? "none": "hsl(0, 0%, 80%);",

                    }
                })
            }}
            placeholder={placeholder}
            components={{
                IndicatorSeparator:null
            }}
            value={value}
            onChange={onChange}
            options={options}
            isDisabled={isDisabled}
        />
    )
}

const CustomInput = (props:CustomInputProps)=>{

    const {
        value,
        onChange,
        disabled = false,
        type
    } = props

    return(
        <VFFilterInputField
            type={type}
            placeholder="Value"
            value={value}
            onChange={onChange}
            disabled={disabled}
            data-testid='text-input'
        />
    )
}

export default VFFilter;