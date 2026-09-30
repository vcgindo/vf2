import { useSpring, animated } from "react-spring";
import { MultiSelectCheckBoxComponent } from "../../../../../components/VectorFLOW/commons/VFMultiFilter/style";
import { useUserData } from "../../../../../context";
import Select from "react-select";
import { useEffect, useState } from "react";
import { DropdownGroupWrapper, SelectDropdownComponent, OptionsWrapper } from "./styles";
import { Filter } from "../../../../../VectorFlow/types/MTO";
import './style.css'
import { InputTypes } from "../Enum";
import { checkValue } from "../../../../../helpers/utils";
import { SCFilterAddButton } from "../../MDM/ViewModify/styles";





interface FilterMultiSelectCheckboxProps {
  filterOptions: Array<{ label: string; id: string }>;
  filterState: Filter;
  header?: string;
  onChange: any;
  filterId?: any;
}


const FilterCheckboxAccordian = ({
  filterType,
  filterKey,
  isOpen,
  setOpenStatus,
  children,
}: any) => {


  
  const openStatusReducer = (prevStatus: any) => {
    Object.keys(prevStatus).forEach((filterType) => {
      if (filterKey !== filterType) {
        prevStatus[filterType] = false;
      }
    });
    return { ...prevStatus, [filterKey]: !prevStatus[filterKey] };
  };

  const openAnimation = useSpring<any>({
    from: { opacity: "0", maxHeight: "25px" },
    to: { opacity: "1", maxHeight: isOpen ? "200px" : "25px" },
    config: { duration: "300" },
  });

  const closeAnimation = useSpring<any>({
    from: { opacity: "0", maxHeight: "0px" },
    to: { opacity: "1", maxHeight: isOpen ? "144px" : "0px" },
    config: { duration: "300" },
  });

  const iconAnimation = useSpring<any>({
    from: {
      transform: "rotate(0deg)",
    },
    to: {
      transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
    },
    config: { duration: "120" },
  });


  return (
    <>
      <animated.div className="filter-accordian" style={openAnimation}>
        <div
          className="accordian-header "
          onClick={() => {
            setOpenStatus(openStatusReducer);
          }}
          style={{ display: "flex", gap: "1rem" }}
        >
          <p
            className="accordian-title"
            style={{ fontWeight: isOpen ? "500" : "" }}
          >
            {filterType}
          </p>
          <animated.img
            style={iconAnimation}
            src="/assets/img/VectorFLOW/BPR/down-arrow.svg"
            data-testid="down-arrow"
          ></animated.img>
        </div>
        <animated.div
          className="accordian-body  custom-scrollbar"
          style={closeAnimation}
        >
          {children}
        </animated.div>
      </animated.div>
    </>
  );
};

const FilterMultiSelectCheckbox = ({
  filterOptions,
  // header,
  onChange,
  filterState,
}: FilterMultiSelectCheckboxProps) => {
  // const colorMap: string[] = ["#9A0101", "#EBBF2B", "#418D18"];
  const { user } = useUserData();
  const themeUi = user.user.theme_ui;
  return (
    <>
      {filterOptions?.map(
        (option: { label: string; id: string }) => {
          // const color = colorMap[index];
          return (
            <>
              <MultiSelectCheckBoxComponent key={option.id} theme={themeUi}>
                <input
                  key={option.id}
                  type="checkbox"
                  name={option.id}
                  style={{
                    width: "15px",
                    height: "20px",
                    marginRight: "14px;",
                    borderRadius: "2px",
                  }}
                  onChange={(e: any) => onChange(e, "value", option)}
                  checked={checkValue(filterState?.value, option.id)}
                />
                <label
                  style={{
                    fontFamily: "Roboto",
                    fontWeight: "300",
                    fontSize: "16px",
                    color: "#313131",
                  }}
                >
                  {option.label}
                </label>
              </MultiSelectCheckBoxComponent>
            </>
          );
        }
      )}
    </>
  );
};

const Checkbox = ({
  filterOptions,
  header,
  onChange,
  filterState,
}: FilterMultiSelectCheckboxProps) => {
  // const colorMap: string[] = ["#9A0101", "#EBBF2B", "#418D18"];
  const { user } = useUserData();

  const themeUi = user.user.theme_ui;
  return (
    <>
      <div
          style={{ display: "flex", gap: "1rem", padding: "10px 0px 10px 20px" }}
        >
          <p>
            {header}
          </p>
        </div>
      <OptionsWrapper >
        {filterOptions?.map(
          (option: { label: string; id: string }) => {
            return (
              <>
                <MultiSelectCheckBoxComponent key={option.id} theme={themeUi}>
                  <input
                    key={option.id}
                    type="checkbox"
                    name={option.id}
                    style={{
                      width: "15px",
                      height: "20px",
                      marginRight: "14px;",
                      borderRadius: "2px",
                    }}
                    onChange={(e: any) => onChange(e, "value", option)}
                    checked={checkValue(filterState?.value, option.id)}
                  />
                  <label
                    style={{
                      fontFamily: "Roboto",
                      fontWeight: "300",
                      fontSize: "16px",
                      color: "#313131",
                    }}
                  >
                    {option.label}
                  </label>
                </MultiSelectCheckBoxComponent>
              </>
            );
          }
        )}
      </OptionsWrapper>
    </>
  );
};


const FilterSelectDropdown = ({
  
  placeholder,
  options,
  hideDropdownArrow,
  onChange,
  filterId,
  value,
  resetKey,
  disabled=false,
}: any) => {

  const { user } = useUserData();
  const themeUi = user.user.theme_ui;
  const customStylesClose = {
    control: (baseStyles:any) => ({
      ...baseStyles,
      height: "39px",
      borderRadius: "20px",
      background: "#F2F2F2",
      cursor: "pointer",
      display: "flex",
      justifyContent: "center",
      border: "1px solid #ccc",
    }),
  
    // OPTION STYLE
    option: (baseStyles:any, state:any) => ({
      ...baseStyles,
      // color: "#313131",
      fontFamily: "Roboto",
      fontWeight: 300,
      fontSize: "12px",
      paddingTop: "6px",
      paddingBottom: "6px",
      cursor: "pointer",
      background: state.isSelected
      ? themeUi === "REGEALBLAZE"
        ? "rgb(252, 163, 17)"
        : "rgb(188, 61, 129)"
        : undefined,
      color:state.isSelected?'white':'black',
      borderBottom: "1px solid #F1F1F1",
      padding:'8px',
      ":hover": {
        background:themeUi==='REGALBLAZE' ? '#fee3b7': '#ebc4d9',
      },
    }),
  
    // MENU LIST (scroll, height limit)
    menuList: (baseStyles:any) => ({
      ...baseStyles,
      background: "#FFFFFF",
      borderRadius: "0 0 20px 20px",
      paddingLeft: "5px",
      marginTop: "0px",
      maxHeight: "150px", 
      overflowY: "auto",
      overflowX: "hidden",

      width: 'max-content',

  
      "&::-webkit-scrollbar": {
        width: "7px",
      },
      "&::-webkit-scrollbar-thumb": {
        background: "#D1D1D1",
      },
    }),
    indicatorsContainer: () => ({
          paddingRight: "10px",
        }),
  
    placeholder: (baseStyles:any) => ({
      ...baseStyles,
      color: "#313131",
      fontFamily: "Roboto",
      fontWeight: 300,
      fontSize: "12px",
      textAlign: "center",
      padding: "0 5px",
    }),
  
    singleValue: (baseStyles:any) => ({
      ...baseStyles,
      color: "#313131",
      fontFamily: "Roboto",
      fontWeight: 300,
      fontSize: "12px",
      padding: "0 5px",
    }),
  };
  

  const customStylesOpen = {
    ...customStylesClose,
    control: (baseStyles: any) => ({
      ...baseStyles,
      height: "39px",
      borderRadius: " 20px 20px 0px 0px",
      background: "#F2F2F2 0% 0% no-repeat padding-box",
    }),
  };

  const [customStyles, setCustomStyles] = useState(customStylesClose);

  const handleMenuOpen = () => {
    setCustomStyles(customStylesOpen);
  };

  const handleMenuClose = () => {
    setCustomStyles(customStylesClose);
  };

 

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
      isDisabled={disabled}
      key={resetKey}
      // menuPlacement="top" 
      

      // menuIsOpen={true}
    />
  );
};


const FilterTextInput = ({
  placeholder,
  onChange,
  disabled = false,
  value,
  type = "text",
  name,
  resetKey,
}: any) => {


  return (
    <input
      name={name}
      type={type}
      disabled={disabled}
      className="no-arrows"
      style={{
        width: "100%",
        height: "38px",
        background: "#F2F2F2 0% 0% no-repeat padding-box",
        borderRadius: "20px",
        outline: "none",
        color: "#313131",
        fontFamily: "Roboto",
        fontWeight: "400",
        fontSize: "14px",
        textAlign: "center",
        // border: "none",
        border: '1px solid rgb(204, 204, 204)',
        cursor: 'text',

      }}
      placeholder={placeholder}
      onChange={onChange}
       value={value}
       key={resetKey}
    />
  );
};



    const textComparators = [
      { value: 'et', label: 'Equal to' },
      { value: 'net', label: 'Not Equal to' },
      { value: "cn", label: "Contains" },
      { value: 'dnc', label: 'Does not contain' },
      { value: 'sw', label: 'Starts with' },
      { value: 'dsw', label: 'Does not start with' },
      { value: 'ew', label: 'Ends with' },
      { value: 'dnew', label: 'Does not end with' }
    ];
    
  const numberComparators = [
    {value:'et', label: '='},
    {value:'net', label: '!='},
    {value:'gte',label:'>='},
    {value:'lte',label:'<='},
    {value:'gt',label:'>'},
    {value:'lt',label:'<'},
  ]

const AvailabilityFilter = ({placeholder, header, onChange,filterId,filterState, setFilterState, masterFilterState, resetKey}:any)=>{

  const getNameOptions = (type: string) => {
    if(type==='numberCompare'){
      return numberComparators
    }
    else{
      return textComparators
    }
  }

  const [selectedHeader, setSelectedHeader] = useState<any>(masterFilterState.filters.map((e:any)=> {return e.header}))
  const [selectedOperator, setSelectedOperator] = useState<any>(masterFilterState.filters.map((e:any)=> {return e.operator}))
  const [selectedValue, setSelectedValue] = useState<any[]>(masterFilterState.filters.map((e:any)=> {return e.value}));

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleHeaderChange = (selectedOption: any, type: any, index:any, id: any) => {

    if(type==="header"){
      const updatedHeaders:any = [...selectedHeader];
      updatedHeaders[index] = selectedOption;

      setSelectedHeader(updatedHeaders);
      const updatedOperator = [...selectedOperator];
      updatedOperator[index] = null;
      setSelectedOperator(updatedOperator);

      const updatedValues = [...selectedValue]; 
      updatedValues[index] = null;
      setSelectedValue(updatedValues);
    }
    else if (type === "operator") {
      const updatedOperator = [...selectedOperator];
      updatedOperator[index] = selectedOption;
      updatedOperator[index].index = index;
      setSelectedOperator(updatedOperator);
      
      onChange(selectedHeader?.[index]?.type,selectedHeader?.[index]?.attributeName, updatedOperator, "orders", updatedOperator?.[index]?.value, selectedHeader?.[index]?.value, [{value: selectedValue?.[index]}],index)
    }
    else if(type==='value'){
    const updatedValues = [...selectedValue]; 
    updatedValues[index] = selectedOption.target.value;
    setSelectedValue(updatedValues);
    const updateOperator = [...selectedOperator];
    updateOperator[index] = selectedOperator[index];
    onChange(selectedHeader?.[index]?.type,selectedHeader?.[index]?.attributeName, updateOperator, "orders", updateOperator?.[index]?.value, selectedHeader?.[index]?.value, [{value: updatedValues?.[index]}],index)
    }
  };

  
  const addFilter = () => {
    setFilterState({
      ...masterFilterState,
      filters: 
      [
      ...masterFilterState.filters, 
      { id: Date.now() }
    ]});    
  };


  useEffect(() => {
    const allHaveValues = selectedHeader.length > 0 && selectedOperator.length > 0 && selectedValue.length > 0 
    if (allHaveValues) {
      const updatedFilterState = masterFilterState?.filters?.map((filter: any, index: any) => ({
        id: filter.id,
        header: selectedHeader[index] || null,
        operator: selectedOperator[index] || null,
        value: selectedValue[index] || '',
      }));
  
      setFilterState((prev: any) => ({
        ...prev,
        filters: updatedFilterState,
      }));
    }

  }, [selectedHeader, selectedOperator, selectedValue]);





  useEffect(() => {
    if(resetKey>0){ 
      setSelectedHeader([]);
      setSelectedOperator([]);
      setSelectedValue([]);
      
      const val = {
        ...masterFilterState,
        filters: 
        [
        { id: Date.now() }
      ]}
      setFilterState(val)
    }
  }, [resetKey]);
  



  const isDisabled = (index: number) => {
    if(selectedHeader[index]===null ||selectedHeader[index]===undefined || selectedHeader[index]==='' ){
     return true;
    }
    else{
      return false;
    }
  };

    const { user } = useUserData();
  const themeUi = user.user.theme_ui;

  const getFilteredHeaderOptions = (index: number) => {

    const selectedKeys = selectedHeader.map((header: any, i: number) => {
    const isDifferentRow = i !== index; 
    const value = header?.value;
    return isDifferentRow ? value : null;
  })
  .filter(Boolean);  
  
    const filteredOptions = header?.filter(
      (e: any) => !selectedKeys.includes(e.name)
    )?.map((e: any) => ({
      key: e.name,
      value: e.name,
      label: e.name,
      type: e.type,
      attributeName: e.attributeName
    })) || [];
  
    return filteredOptions;
  };

  

      return (
      <>
      {masterFilterState?.filters?.map((filter: any, index: any) => (
      <div key={filter.id} style={{ display: "flex",  width: index === 0 ? "100%" : "90%"}}>
    
      <div style={{ display: "flex", justifyContent: "space-between", width: index === 0 ? 'calc(100% - 40px)' : '100%' }}>
      <DropdownGroupWrapper>
        <SelectDropdownComponent style={{ width:'100%' }}>
          <FilterSelectDropdown
            className="custom-scrollbar"
            placeholder={"Select"}
            options={getFilteredHeaderOptions(index)}
            onChange={(option: any) => handleHeaderChange(option, 'header', index, filter.id)}
            filterId={filterId}
            value={selectedHeader?.[index]}
            resetKey={resetKey}
          />
        </SelectDropdownComponent>

        <SelectDropdownComponent style={{width:'100%',cursor: isDisabled(index) ? 'default' : 'pointer' }}>
          <FilterSelectDropdown 
            className="custom-scrollbar"
            placeholder={'Operator'}
            type={filterState.type === InputTypes.TextCompare ? "text" : "number"}
            options={getNameOptions(selectedHeader?.[index]?.type)}
            hideDropdownArrow
            key={new Date()} 
            onChange={(e: any) => handleHeaderChange(e, 'operator', index, filter.id)}
            filterId={filterId}
            value={selectedOperator?.[index] || null}
            disabled={isDisabled(index)}
            resetKey={resetKey}
          />
        </SelectDropdownComponent>

        <SelectDropdownComponent style={{ width: "100%" }}>
          <FilterTextInput
            name={header}
            type={selectedHeader[index]?.type === InputTypes.TextCompare ? "text" : "number"}
            placeholder={"Value"}
            onChange={(e: any) => handleHeaderChange(e, 'value', index, filter.id)}
            header={header}
            value={selectedValue?.[index] || ''}
            disabled={isDisabled(index)}
            resetKey={resetKey}
          />
        </SelectDropdownComponent>
      </DropdownGroupWrapper>
    </div>

   
  {index === 0 && (() => {
  const filteredOptions = getFilteredHeaderOptions(index);
  const isDisabled = filteredOptions.length === 1;

  return (
    <div
      style={{
        width: "40px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        opacity: isDisabled ? 0.5 : 1,
        cursor: isDisabled ? "not-allowed" : "pointer",
      }}
    >
      <SCFilterAddButton
        onClick={isDisabled ? undefined : addFilter}
        src={
          themeUi === "REGALBLAZE"
            ? "/assets/img/VectorFLOW/NMS/add-filter-regal.svg"
            : "/assets/img/VectorFLOW/NMS/add-filter.svg"
        }
        data-testid="add-filter"
      />
    </div>
  );
})()}



  </div>

  
))}

      </>
    );
  };


export {
  FilterCheckboxAccordian,
  FilterMultiSelectCheckbox,
  FilterSelectDropdown,
  FilterTextInput,
  AvailabilityFilter,
  textComparators,
  numberComparators,
  Checkbox,
};
