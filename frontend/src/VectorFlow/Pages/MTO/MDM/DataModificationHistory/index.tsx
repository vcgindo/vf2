import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import { FilterWrapper,SelectSearchWrapper,ButtonWrapper,VerticalDivider, SelectWrapper, TextWrapper,DropDownWrapper,DualDropDownWrapper,ArroWrapper } from "./styles";
import { useUserData } from "../../../../../context";
import Select from 'react-select'
import useDataModificationHistory from "./useDataModificationHistory";
import VFTable from "../../Common/VFTable";


const MTODataModificationHistory = ()=>{
 
  
  const {
    colDefs,
    rowData,
    options,
    skuOptions,
    locOptions,
    handleChange,
    handleReset,
    // setSelectedOption,
    setSelectedSkuOption,
    setSelectedLocOption,
    selectedOption,
    selectedSkuOption,
    selectedLocOption,
    isSkuDisabled,
    isLocDisabled,
    onMasterChange
   
    
} = useDataModificationHistory()

  
const styles={
    option:(baseStyles:any, { isSelected }:any) => ({
      ...baseStyles,
      backgroundColor: isSelected ?theme_ui==="REGALBLAZE"?"#FCA311": "#BC3D80" : "white",
      fontSize:'12px',
      "&:hover": {
        // backgroundColor: '#bc3d814d',
        color:"black",
        backgroundColor:theme_ui==="REGALBLAZE"?"rgb(252, 163, 17,0.3) ": '#bc3d814d',
      }
      }),
    control:(baseStyles:any, { isFocused }:any) => ({ 
      ...baseStyles, 
      borderColor: isFocused ? "none": "hsl(0, 0%, 80%);",
      fontSize:'12px',
      boxShadow: 'none',
      "&:hover":{
          borderColor: isFocused ? "none": "hsl(0, 0%, 80%);",

      }
    }),
}
const specificStyles = {
    control: (baseStyles:any, {isFocused}:any) => ({
      ...baseStyles,
        borderColor: isFocused ? "none": "hsl(0, 0%, 80%);",
        fontSize:'12px',
        width:'170px',
        boxShadow: 'none',
        "&:hover":{
          borderColor: isFocused ? "none": "hsl(0, 0%, 80%);"
        }
      }),
};

const {user} = useUserData()
const theme_ui = user.user.theme_ui

  return (
    <>
    <FilterWrapper>
        <SelectSearchWrapper>
          <SelectWrapper>
            <TextWrapper>
            {/* <img src={themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/BPR/eye-filled-regal.svg":"/assets/img/VectorFLOW/BPR/eye-filled-purple.svg"}/> */}

              < img src= {theme_ui==="REGALBLAZE"?"/assets/img/VectorFLOW/NMS/01-RegalBlaze.svg":"/assets/img/VectorFLOW/NMS/01.svg"}/>
              <p>Select Master</p>
            </TextWrapper>
            <DropDownWrapper>
              <Select options={options} value={selectedOption} placeholder={"Select Master"} styles={styles} onChange={(newValue: any)=>{onMasterChange(newValue)}}></Select>
            </DropDownWrapper>
          </SelectWrapper>

          <ArroWrapper>
            <img src="/assets/img/VectorFLOW/NMS/arrow.svg"></img>
          </ArroWrapper>

          <SelectWrapper>
            <TextWrapper>

              <img src= {theme_ui==="REGALBLAZE"?"/assets/img/VectorFLOW/NMS/02-RegalBlaze.svg":"/assets/img/VectorFLOW/NMS/02.svg"} style={{marginLeft:'-20px'}}></img>
              <p>Search Key</p>
            </TextWrapper>
            <DualDropDownWrapper>
              <Select options={skuOptions} value={selectedSkuOption} placeholder={"Select SKU Code"} styles={{...styles,...specificStyles}} onChange={(newValue: any)=>{setSelectedSkuOption(newValue)}} isDisabled={isSkuDisabled()} ></Select>
              <Select options={locOptions} value={selectedLocOption} placeholder={"Select Location"} styles={{...styles,...specificStyles}} onChange={(newValue: any)=>{setSelectedLocOption(newValue)}} isDisabled={isLocDisabled()}></Select>
            </DualDropDownWrapper>
          </SelectWrapper>
            
        </SelectSearchWrapper>
        <VerticalDivider />
        <ButtonWrapper>
          <VFButton onClick={()=>handleChange()} themeUi={theme_ui} width={175}>Submit</VFButton>
          <VFButtonOutline onClick={handleReset} themeUi={theme_ui} width={175}>Reset</VFButtonOutline>
        </ButtonWrapper>
    </FilterWrapper>

    <VFTable
        columnDefs={colDefs}
        rowData={rowData}
        enableRangeSelection={true} 
        pagination={true}
        rowSelection="multiple"
          statusBar = {{
            statusPanels: [
            { statusPanel: 'agTotalAndFilteredRowCountComponent', align:'left' },
            { statusPanel: 'agTotalRowCountComponent', align:'left' },
            { statusPanel: 'agFilteredRowCountComponent', align:'left' },
            { statusPanel: 'agSelectedRowCountComponent', align:'left' },
            { statusPanel: 'agAggregationComponent', align:'left' },
            ],
          }} 
        height={'70%'}
      />    
    </>
  )

}
export default MTODataModificationHistory;


