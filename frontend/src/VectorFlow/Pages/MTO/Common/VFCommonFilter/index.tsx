import { Filter, FilterState } from "../../../../../VectorFlow/types/MTO";
import { useUserData } from "../../../../../context";
import {
  ButtonContainer,
  ButtonFilterWrapper,
  ConfirmationText,
  FilterBody,
  FilterCardWrapper,
  FilterComponent,
  FilterHeader,
  FilterWrapper,
  TextBtn,
} from "./styles";
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard";
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";
import React, { useEffect, useState } from "react";
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import { AvailabilityFilter, FilterCheckboxAccordian, FilterMultiSelectCheckbox, Checkbox } from "./InputTypes";
import VFMasterFieldSearch from "../../../../../components/VectorFLOW/commons/VFMasterFieldSearch";
import { checkValue } from "../../../../../helpers/utils";
import { InputTypes } from "../Enum";
import _ from "lodash";

interface VFCommonFilterProps {
  onApplyFilter: (params: any) => void;
  onGoBack: () => void;
  selectedOption?: () => void;
  toggleAdd?: () => void;
  placeholder?: string;
  multiFilter: FilterState;
  setMultiFilter: any;
  isFilterOpen: boolean;
}

const VFCommonFilter = (props: VFCommonFilterProps) => {
  const { onGoBack, multiFilter, setMultiFilter, onApplyFilter, isFilterOpen } = props;
  const [filterState, setFilterState] = useState<any>({});
  const [openStatus, setOpenStatus] = useState<any>({});
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState<boolean>(false);
  const { user } = useUserData();
  const [isCCDisabled, setIsCCDisabled] = useState(props.multiFilter.customers?.filters[1]?.value?.length > 0);
  const [isCNDisabled, setIsCNDisabled] = useState(props.multiFilter.customers?.filters[0]?.value?.length > 0);

  const themeUi = user.user.theme_ui;

  const [resetKey, setResetKey] = useState(0);

  const onFilterChange = (type: string, filterId: string, e: any, parent: string, property: string, header?: string, targetValue?: any, currIndex?: any) => {

    let updatedFilters = filterState[parent as keyof FilterState]?.filters || [];
    if(type==='numberCompare' || type==='textCompare'){
      updatedFilters = filterState[parent as keyof FilterState]?.filters.map((ele:any)=>{
        if (ele.index != null && currIndex != null && String(ele.index) === String(currIndex)) {
          const newEle = _.cloneDeep(ele);
          newEle.index = undefined;
          newEle.operator = "";
          newEle.value = [];
          return newEle;
        }
        else{
          return ele;
        }
      })
      
      
     updatedFilters = updatedFilters.map((ele:any)=>{
        if(ele.attributeName===filterId ){
          const newEle = _.cloneDeep(ele);
          newEle.operator = property
          newEle.value=targetValue
          newEle.index = currIndex;
          return newEle;
        }
        else{
          return ele;
        }
      })
    }

    for (let i = 0; i < updatedFilters.length; i++) {
      const { attributeName } = updatedFilters[i];
      
      if (attributeName === filterId) {
        if( type === InputTypes.TextCompare || type === InputTypes.NumberCompare){
          let val = e?.value;
          if(property === 'value'){
            const updatedvalue = type === InputTypes.NumberCompare ? e.target.value !== ''  && e.target.value != undefined  ? Number(e?.target?.value): e?.target?.value: e.target.value;
            val =  [{label: updatedvalue, value: updatedvalue}];
          }
          
          updatedFilters[i][property as keyof Filter]= val;
        }

        if( type === InputTypes.MultiSelect ||type === InputTypes.Checkbox){
          if (checkValue(updatedFilters[i].value, targetValue?.id)) {
            updatedFilters[i].value = updatedFilters[i]?.value?.filter((v: any) => v?.value !== targetValue?.id );
          } else {
            updatedFilters[i].value = [...updatedFilters[i].value, {label: targetValue?.label, value: targetValue?.id }];
          }
        }

        if( type === InputTypes.Search){
          if(Array.isArray(e)){
            updatedFilters[i].value = e?.map((option) => option);
          }
        }

        if( type === InputTypes.Select){
          updatedFilters[i].value = e.target.name === updatedFilters[i].value[0] ? [] : [e.target.name];
        }
      }
    }


    if(filterState.customers?.filters[0].value.length===0){
      setIsCNDisabled(false);
    }
    if(filterState.customers?.filters[1].value.length===0){
      setIsCCDisabled(false);
    }
    const val = {
      ...filterState,
      [parent]: {
        ...filterState[parent as keyof FilterState],
        filters: [...updatedFilters],
      },
    };

    setFilterState(val);
  };

  const clearFilters = (currFilters: any) => {
    setResetKey(prev => prev + 1); 

    const emptyFilterState = { ...currFilters };
    for(const key in emptyFilterState){
      
      const { filters } = emptyFilterState[key];
      for (let i = 0; i < (filters?.length); i++) {
        const { attributeName, options } = filters[i];
        filters[i].value = [];
      }
    }

    emptyFilterState.filters = [{id: Date.now()}];
    
    setMultiFilter(emptyFilterState);
    setFilterState(emptyFilterState);
  }

  useEffect(() => {
    const openFilters: any = {};

    const categories = Object.keys(filterState);

    for (let c = 0; c < categories.length; c++) {
      const filters = filterState[categories[c] as keyof FilterState]?.filters || [];
      for (let f = 0; f < filters.length; f++) {
        const { type, attributeName } = filters[f];
        if ( type === InputTypes.MultiSelect || type === InputTypes.Select ) {
          openFilters[attributeName] = false;
        }
      }
    }
    setOpenStatus(openFilters);
  }, []);

  useEffect(() => {
    if (Object.keys(multiFilter).length) {
      if(resetKey>0){
        setFilterState({...JSON.parse(JSON.stringify(multiFilter)), filters:  [{id: Date.now()}]});
        setResetKey(0);
      }
      else{
        setFilterState({...JSON.parse(JSON.stringify(multiFilter)), filters: multiFilter?.filters || [{id: Date.now()}]});

      }
    }
  }, [multiFilter]);



  const filterKeys = Object.keys(filterState) || [];

  return (
    <>
      <VFModalCard
        zoom={"0.73"}
        openModal={isFilterOpen}
        closeModal={onGoBack}
        headerIcon={"/assets/img/VectorFLOW/BPR/select-filter.svg"}
        headerText={"Select Filter"}
        closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}
        paddingLeftAndRight={0}
        backgroundColor={"#f4f4f4"}
        data-testid="vfmultifilter-img"
      >
        {filterKeys.length === 0 ? 
          <div data-testid="filter-loader" className="loading" style={{ height: '300px' }}>
            <VFLoader/> 
          </div>
          : 
          <React.Fragment>
            <FilterBody>
              {filterKeys?.map((category) => {
                 let hasRenderedComponent = false;
                if(category==="filters")return null;
                return (
                  <FilterCardWrapper data-testid="availabilityFilter">
                    <FilterHeader>
                      <p>{filterState[category as keyof FilterState]?.label}</p>
                    </FilterHeader>
                    <FilterWrapper className="drop-down-options">
                      {filterState[category as keyof FilterState]?.filters?.map((filter: Filter) => {
                       if (filter.attributeName === "ms" && (filter.options.length === 0)) {
                        return null; 
                      }
                      if (
                        (filter?.type === InputTypes.TextCompare || filter?.type === InputTypes.NumberCompare) && hasRenderedComponent
                      ) {
                        return null;
                      }

                      if (filter?.type === InputTypes.TextCompare || filter?.type === InputTypes.NumberCompare) {
                        hasRenderedComponent = true; 
                        return (
                          <FilterComponent data-testid="" style={{ borderTop: "0.5px solid #B7B7B7" }}>
                            <AvailabilityFilter
                              placeholder={filter?.name}
                              onChange={
                                onFilterChange  
                              }
                              header={filterState[category as keyof FilterState]?.filters.filter((ele:any)=> ele.type==='numberCompare' || ele.type==='textCompare')}
                              filterState={filter}
                              masterFilterState={filterState}
                              setFilterState={setFilterState}
                              filterId={filter?.attributeName}
                              resetKey={resetKey}
                            />
                          </FilterComponent>
                        );
                      }

                        if (filter.type === InputTypes.Search) {
                          return (
                            <FilterComponent
                              style={{
                                borderTop: "0.5px solid #B7B7B7",
                                marginBottom: "5px",
                              }}
                            >
                              <VFMasterFieldSearch
                                value={filter.value}
                                setValue={(e: any) =>{
                                  if(filter.attributeName==='cc'){
                                    setIsCNDisabled(true);
                                  }
                                  else if(filter.attributeName==='cn'){
                                    setIsCCDisabled(true);
                                  }
                                  onFilterChange(InputTypes.Search, filter.attributeName, e, category, "value")
                                }}
                                options={filter.options?.map((f: any) => ({
                                  label: f.label,
                                  value: f.value,
                                }))}
                                placeholder={`${filter.name}`}
                                handleListChild={() => {return null}}
                                maxToShow={3}
                                backgroundColor={"#F2F2F2"}
                                borderRadius={40}
                                disabled={filter.attributeName==='cc'?(isCCDisabled):(filter.attributeName==='cn'?(isCNDisabled): false)}
                                boxShadow={"0"}
                              />
                            </FilterComponent>
                          );
                        }

                        if (filter.type === InputTypes.Select) {
                          return (
                            <FilterComponent
                              style={{
                                borderTop: "0.5px solid #B7B7B7",
                                height: openStatus[filter.attributeName] ? "unset" : "50px",
                              }}
                            >
                              <FilterCheckboxAccordian
                                filterType={filter.name}
                                filterKey={filter.attributeName}
                                isOpen={openStatus[filter.attributeName]}
                                setOpenStatus={setOpenStatus}
                              >
                                <FilterMultiSelectCheckbox
                                  header={filter.name}
                                  filterOptions={filter.options?.map((f: any) => ({ label: f.label, id: f.value }))}
                                  filterState={filter}
                                  onChange={(e: any, key: string) =>
                                    onFilterChange(InputTypes.Select, filter.attributeName, e, category, key)
                                  }
                                  filterId={filter.attributeName}
                                />
                              </FilterCheckboxAccordian>
                            </FilterComponent>
                          );
                        }
                      
                        if (filter.type === InputTypes.Checkbox) {
                          return (
                            <FilterComponent
                              style={{
                                borderTop: "0.5px solid #B7B7B7",
                                height: "90px",
                              }}
                            >
                                <Checkbox
                                  header={filter.name}
                                  filterOptions={filter.options?.map((f: any) => ({ label: f?.label, id: f?.value || f.label }))}
                                  filterState={filter}
                                  onChange={(e: any, key: string, targetVal: any) =>
                                    onFilterChange(InputTypes.Checkbox, filter.attributeName, e, category, key, '', targetVal)
                                  }
                                  filterId={filter.attributeName}
                                />
                            </FilterComponent>
                          );
                        }
                        
                        if (filter.type === InputTypes.MultiSelect && filter.options?.length !== 0) {
                        
                          return (
                            <FilterComponent
                              style={{
                                borderTop: "0.5px solid #B7B7B7",
                                height: openStatus[filter.attributeName] ? "unset" : "50px",
                              }}
                            >
                              <FilterCheckboxAccordian
                                filterType={filter.name}
                                filterKey={filter.attributeName}
                                isOpen={openStatus[filter.attributeName]}
                                setOpenStatus={setOpenStatus}
                              >
                                <FilterMultiSelectCheckbox
                                  header={filter.name}
                                  filterOptions={filter?.options?.map((f: any) => ({ label: f.label, id: f.value }))}
                                  filterState={filter}
                                  onChange={(e: any, key: string, targetVal: any) =>
                                    onFilterChange(InputTypes.MultiSelect, filter.attributeName, e, category, key,"", targetVal)
                                  }
                                  filterId={filter.attributeName}
                                />
                              </FilterCheckboxAccordian>
                            </FilterComponent>
                          );
                        }

                      })}
                    </FilterWrapper>
                  </FilterCardWrapper>
                );
              })}
            </FilterBody>
            <ButtonFilterWrapper>
              <ButtonContainer>
                <TextBtn onClick={() => setIsConfirmModalOpen(true)} theme={themeUi}>Clear All Filters</TextBtn>
                <VFButtonOutline data-testid="goBack" themeUi={user.user.theme_ui} onClick={ () => {
                  setFilterState(multiFilter);
                  onGoBack()
                }
                }>
                  Go Back!
                </VFButtonOutline>
                <VFButton data-testid="applyFilter" themeUi={user.user.theme_ui} onClick={() =>{
                  setMultiFilter(filterState);
                  onApplyFilter(filterState);
                }}>
                  Apply Filter
                </VFButton>
              </ButtonContainer>
            </ButtonFilterWrapper>
          </React.Fragment>
        }
      </VFModalCard>
        <VFModalCard
          zoom={"0.73"}
          openModal={isConfirmModalOpen}
          closeModal={() => setIsConfirmModalOpen(false)}
          headerText={'Warning'} 
          headerIcon={'/assets/img/ist/warning.svg'}
          closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}
          paddingLeftAndRight={0}
          backgroundColor={"#f4f4f4"}
          data-testid="vfmultifilter-img"
        >
          <ConfirmationText>Are you sure, want to clear all Selected Filters ?</ConfirmationText>
          <ButtonFilterWrapper>
              <ButtonContainer>
                <VFButtonOutline data-testid="goBack" themeUi={user.user.theme_ui} onClick={ () => {
                  setIsConfirmModalOpen(false)
                }}>
                  No
                </VFButtonOutline>
                <VFButton data-testid="applyFilter" themeUi={user.user.theme_ui} onClick={() =>{
                  clearFilters(filterState);
                  setIsConfirmModalOpen(false)
                }}>
                  Yes
                </VFButton>
              </ButtonContainer>
            </ButtonFilterWrapper>
        </VFModalCard>
    </>
  );
};

export default VFCommonFilter;
