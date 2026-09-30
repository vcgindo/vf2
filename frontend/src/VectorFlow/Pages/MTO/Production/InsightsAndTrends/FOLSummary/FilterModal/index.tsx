import { useState, useEffect } from 'react';
import VFButtonOutline from '../../../../../../../components/VectorFLOW/commons/VFButtonOutline';
import VFButton from '../../../../../../../components/VectorFLOW/commons/VFButton';
import VFModalCard from '../../../../../../../components/VectorFLOW/commons/VFModalCard';

import { AccordianContainer, ButtonContainer, ButtonFilterWrapper, FilterAccordianWrapper, FilterContainer, FilterHeading, HorizontalLine, ModalBody, Option, OptionsWrapper } from './styles';
import FilterCheckboxAccordian from '../../../../../../../components/VectorFLOW/commons/MTO/FilterCheckboxAccordian';
import { DropdownGroupWrapper, FilterComponent, SelectDropdownComponent } from '../../../../../../../components/VectorFLOW/commons/VFMultiFilter/style';
import VFMasterFieldSearch from '../../../../../../../components/VectorFLOW/commons/VFMasterFieldSearch';
import Select from 'react-select';
import Radio from '../../../../../../../components/VectorFLOW/commons/MTO/Radio';
// import VFMasterFieldSearch from '../../../../../../components/VectorFLOW/commons/VFMasterFieldSearch';


const FilterSelectDropdown = ({ placeholder, options, hideDropdownArrow, onChange, filterId, value }: any) => {


    const customStylesClose = {
        control: (baseStyles: any) => (
            {
                ...baseStyles,
                height: '39px',
                borderRadius: ' 20px 20px 20px 20px',
                background: '#F2F2F2 0% 0% no-repeat padding-box',
                // border: 'none',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'center',


                border: '1px solid rgb(204, 204, 204)'

            }
        ),
        indicatorsContainer: () => ({
            paddingRight: '10px',
        }),
        option: (baseStyles: any) => (
            {
                ...baseStyles,
                color: '#313131',
                fontFamily: 'Roboto',
                fontWeight: '300',
                fontSize: '16px',
                // marginTop:'5px',
                // marginBottom:'5px',
                // marginLeft:'5px',
                paddingTop: '3px',
                paddingBottom: '3px',
                cursor: 'pointer',
                borderTop: '1px solid #B7B7B7',
            }
        ),
        menuList: (baseStyles: any) => (
            {
                ...baseStyles,
                borderRadius: '0px 0px 20px 20px',
                background: '#F2F2F2 0% 0% no-repeat padding-box',
                paddingLeft: '5px',
                marginTop: '0px',
                overflowY: 'overlay',
                overflowX: 'hidden',

                '&::-webkit-scrollbar': {
                    width: '7px',
                },
                '&::-webkit-scrollbar-track': {
                    borderRadius: '30px',
                    opacity: 1,
                },
                '&::-webkit-scrollbar-thumb': {
                    width: '7px',
                    background: '#D1D1D1 0% 0% no-repeat padding-box',
                    boxShadow: '0px 6px 9px #F8F8F8',
                    borderRadius: '30px',
                    opacity: 1,
                },
            }
        ),
        placeholder: (baseStyles: any) => (
            {
                ...baseStyles,
                // marginLeft:hideDropdownArrow ? '' : '23px',
                color: '#313131',
                fontFamily: 'Roboto',
                fontWeight: '300',
                fontSize: '16px',
                textAlign: hideDropdownArrow ? 'center' : '',
                padding: '0 5px',
                boxSizing: "border-box"
            }
        ),
        singleValue: (baseStyles: any) => (
            {
                ...baseStyles,
                // marginLeft:'23px',
                // marginRight:hideDropdownArrow ? '23px' : '23px',
                color: '#313131',
                fontFamily: 'Roboto',
                fontWeight: '300',
                fontSize: '16px',
                textAlign: hideDropdownArrow ? 'center' : '',
                padding: '0 5px',
                boxSizing: "border-box"
            }
        ),

    }

    const customStylesOpen = {
        ...customStylesClose,
        control: (baseStyles: any) => ({
            ...baseStyles,
            height: '39px',
            borderRadius: ' 20px 20px 0px 0px',
            background: '#F2F2F2 0% 0% no-repeat padding-box',
        })
    }

    const [customStyles, setCustomStyles] = useState(customStylesClose);

    const handleMenuOpen = () => {
        setCustomStyles(customStylesOpen);
    }

    const handleMenuClose = () => {
        setCustomStyles(customStylesClose);
    }

    return (
        <Select
            options={options}
            isClearable={false}
            unstyled={true}
            styles={customStyles}
            placeholder={placeholder}
            isSearchable={false}
            onMenuOpen={handleMenuOpen}
            onMenuClose={handleMenuClose}
            onChange={onChange}
            aria-label={filterId}
            value={value}
        // menuIsOpen={true}
        />
    )
}

const FilterTextInput = ({ placeholder, onChange, disabled = false, value }: any) => {
    return (
        <input type="number" disabled={disabled} style={{ width: '100%', height: '38px', background: '#F2F2F2 0% 0% no-repeat padding-box', borderRadius: '20px', outline: 'none', color: '#313131', fontFamily: 'Roboto', fontWeight: '300', fontSize: '16px', textAlign: 'center', border:'1px solid rgb(204, 204, 204)'
        }} placeholder={placeholder} onChange={onChange} value={value} />
    )
}


interface IFilterModalProps {
    isOpen: boolean;
    filters: { key: string, heading: string, options: string[] }[];
    handleOkay: (selectedOptions: any) => void;
    handleClose: () => void;
    selectedOptions: any;
    handleOptionSelect: (e: any, heading: string, index: number) => void;
    handleNameChange: (e: any) => void;
    themeUi?: string;
    handleFolChange: (folfilterSymbol: string, folFilterValue: string) => void;
}


const AvailabilityFilter = ({ header, filterId, handleFolChange, selectedOptions }: any) => {
    const comparisionOptions = [
        { value: 'equalto', label: 'Equal to' },
        { value: 'notequalto', label: 'Not Equal to' },
        { value: 'greaterthan', label: '>' },
        { value: 'greaterthanequalto', label: '>=' },
        { value: 'smallerthan', label: '<' },
        { value: 'smallerthanequalto', label: '<=' },
    ]

    const [folFilterSymbol, setfolFilterSymbol] = useState(selectedOptions?.folfilter?.symbol || "");
    const [folFilterValue, setFolFilterValue] = useState(selectedOptions?.folfilter?.value || "");

    return (
        <>
            <DropdownGroupWrapper>

                <SelectDropdownComponent data-testid="BPR-filter-dropdown">
                    <FilterTextInput disabled={true} placeholder={"Fol"} />
                </SelectDropdownComponent>



                <SelectDropdownComponent data-testid="BPR-filter-dropdown">
                    <FilterSelectDropdown
                        className="custom-scrollbar"
                        placeholder={folFilterSymbol}
                        options={comparisionOptions}
                        hideDropdownArrow
                        onChange={(e: any) => {
                            setfolFilterSymbol(e.label),
                            handleFolChange(e.label, folFilterValue)
                        }}
                        filterId={filterId}
                        value={folFilterSymbol}
                    />
                </SelectDropdownComponent>
                <SelectDropdownComponent data-testid="BPR-filter-dropdown">
                    <FilterTextInput
                        placeholder={folFilterValue}
                        onChange={(e: any) => {
                            setFolFilterValue(e.target.value),
                            handleFolChange(folFilterSymbol, e.target.value)
                        }}
                        header={header}
                        value={folFilterValue}
                    />
                </SelectDropdownComponent>
            </DropdownGroupWrapper>
        </>
    )
}


const FilterModal = (props: IFilterModalProps) => {

    const {
        isOpen,
        handleClose,
        handleOkay,
        filters,
        selectedOptions,
        handleOptionSelect,
        handleNameChange,
        themeUi,
        handleFolChange,
    } = props;

    const [activeAccordian, setActiveAccordian] = useState<string>('');

    const handleChange = (event: any) => {
        const PlantArray = [];

        for (let index = 0; index < event?.length; index++) {
            // const element = event[index].value
            PlantArray.push(event[index])

        }
        handleNameChange(PlantArray);
    }

    const handleOptionChange = (e: any, heading: string, index: number) => {
        handleOptionSelect(e, heading, index)
    }

    const getChecked = (heading: string, option: string) => {
        if (heading === 'Product Group') {
            return selectedOptions?.productGroup?.includes(option);
        }

        if (heading === 'Department') {
            return selectedOptions?.department[option]
        }

        if (heading === 'CCR Group') {
            return selectedOptions?.ccrGroup[option]
        }

        if (heading === 'CCR') {
            return selectedOptions?.ccrName[option]
        }
    }

    const handleToggleAccordian = (key: string) => {
        if (key === activeAccordian) {
            setActiveAccordian('');
        } else {
            setActiveAccordian(key);
        }
    }

    return (
        <VFModalCard
            zoom={'0.7'}
            openModal={isOpen}
            headerIcon=""
            headerText="Select Filter"
            closeIcon="/assets/img/VectorFLOW/NMS/close-dark.svg"
            closeModal={handleClose}
            paddingLeftAndRight={0}
            backgroundColor="rgb(244, 244, 244)"
        >
            <ModalBody>
                <FilterContainer>
                    <FilterHeading>Resource Filters</FilterHeading>
                    <HorizontalLine></HorizontalLine>
                    {/* <SearchBar>
                        <PlantInput
                            id={'plntNmInput'}
                            data-testid="plntNmInput"
                            name='plantName'
                            placeholder='Plant'
                            value={selectedOptions?.plantName}
                            onChange={(e) => handleChange(e)}
                        />
                        <img
                            src="/assets/img/search-icon.svg"
                            alt="search-icon"
                        />
                    </SearchBar> */}
                    <FilterAccordianWrapper>

                    <VFMasterFieldSearch
                        value={selectedOptions?.plantName}
                        setValue={(e: any) => {
                            if (e) {
                                
                                if (e.length >= 0) {
                                    handleChange(e)
                                }
                            }
                        }}
                        
                        options={filters[0].options}
                        placeholder={'Plant'}
                        handleListChild={() => null}
                        maxToShow={3}
                        backgroundColor={'#F2F2F2'}
                        borderRadius={40}
                        disabled={false}
                        boxShadow={'0'}
                        />
                    </FilterAccordianWrapper>
                    <FilterAccordianWrapper>
                        {
                            filters?.map((filter: { key: string, heading: string, options: string[] }) => {
                                if (filter.key === "plnm" || filter.key === "FOL" || filter.key === "prdGrp") return null
                                return (
                                    <AccordianContainer>
                                        <FilterCheckboxAccordian filterType={filter?.heading} filterKey={filter?.key} isOpen={activeAccordian === filter?.key} handleToggleAccordian={handleToggleAccordian}>
                                            <OptionsWrapper>
                                                {filter?.options?.map((option: string, idx: number) =>

                                                (
                                                    <Option>
                                                        <label style={{ alignItems: 'center', display: 'flex', cursor:'pointer', gap: '8px' }}>
                                                                <Radio
                                                                key={option}
                                                                name={option}
                                                                theme={themeUi ? themeUi : ''}
                                                                checked={getChecked(filter?.heading, option)}
                                                                onChange={(e) => { handleOptionChange(e, filter?.heading, idx) }}
                                                                type={`${filter.key === 'prdGrp' ? 'radio' : 'checkbox'}`}
                                                            />
                                                            {option}
                                                        </label>
                                                        {/* <input
                                                            key={option}
                                                            name={option}
                                                            checked={getChecked(filter?.heading, option)}
                                                            onChange={(e) => { handleOptionChange(e, filter?.heading, idx) }}
                                                            type='checkbox'
                                                        />
                                                        <label>{option}</label> */}
                                                    </Option>
                                                ))}
                                            </OptionsWrapper>
                                        </FilterCheckboxAccordian>
                                    </AccordianContainer>)
                            })
                        }
                        <FilterComponent style={{ borderTop: '0.5px solid #E1E2E8', padding: '15px' }} >
                            <AvailabilityFilter
                                handleFolChange={handleFolChange}
                                header="Location Filter"
                                filterId={'LF1'}
                                filterState={filters}
                                selectedOptions={selectedOptions}
                            />
                                
                                
                        </FilterComponent>
                    </FilterAccordianWrapper>

                </FilterContainer>
            </ModalBody>
            <ButtonFilterWrapper>
                <ButtonContainer>
                    <VFButtonOutline themeUi={themeUi || ''} onClick={handleClose}>Go Back!</VFButtonOutline>
                    <VFButton themeUi={themeUi || ''} onClick={() => handleOkay(selectedOptions)}>Apply Filter</VFButton>
                </ButtonContainer>
            </ButtonFilterWrapper>
        </VFModalCard>
    )
}

export default FilterModal;
