import { useState } from 'react';
import VFButtonOutline from '../../../../../../components/VectorFLOW/commons/VFButtonOutline';
import VFButton from '../../../../../../components/VectorFLOW/commons/VFButton';
import VFModalCard from '../../../../../../components/VectorFLOW/commons/VFModalCard';

import { AccordianContainer, ButtonContainer, ButtonFilterWrapper, FilterAccordianWrapper, FilterContainer, FilterHeading, HorizontalLine, ModalBody, Option, OptionsWrapper, } from './styles';
import FilterCheckboxAccordian from '../../../../../../components/VectorFLOW/commons/MTO/FilterCheckboxAccordian';
import VFMasterFieldSearch from '../../../../../../components/VectorFLOW/commons/VFMasterFieldSearch';
import Radio from '../../../../../../components/VectorFLOW/commons/MTO/Radio';



interface IFilterModalProps {
    isOpen: boolean;
    filters: { key: string, heading: string, options: string[] }[];
    handleOkay: (selectedOptions: any) => void;
    handleClose: () => void;
    selectedOptions: any;
    handleOptionSelect: (e: any, heading: string, index: number) => void;
    handleNameChange: (e: any) => void;
    themeUi?: string;
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
        themeUi
    } = props;

    const [activeAccordian, setActiveAccordian] = useState<string>('');

    const handleChange = (event: any) => {
        const PlantArray = [];
         for (let index = 0; index < event?.length; index++) {
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
            {/* <ModalWrapper> */}
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
                                handleListChild={() => { console.log("child change") }}
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
                                    if (filter.key === "plnm") return null
                                    return (
                                        <AccordianContainer>
                                            <FilterCheckboxAccordian filterType={filter?.heading} filterKey={filter?.key} isOpen={activeAccordian === filter?.key} handleToggleAccordian={handleToggleAccordian}>
                                                <OptionsWrapper>
                                                    {filter?.options?.map((option: string, idx: number) => (
                                                        <Option >

                                                            <label style={{ alignItems: 'center', display: 'flex', cursor:'pointer', gap: '8px' }}>
                                                                <Radio
                                                                key={option}
                                                                name={option}
                                                                theme={themeUi ? themeUi : ''}
                                                                checked={getChecked(filter?.heading, option)}
                                                                onChange={(e) => { handleOptionChange(e, filter?.heading, idx) }}
                                                                type={`${filter.key === 'prdGrp' ? 'radio' : 'checkbox'}`}
                                                            />{option}</label>
                                                        </Option>
                                                    ))}
                                                </OptionsWrapper>
                                            </FilterCheckboxAccordian>
                                        </AccordianContainer>)
                                })
                            }

                        </FilterAccordianWrapper>

                    </FilterContainer>
                </ModalBody>
            {/* </ModalWrapper> */}

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
