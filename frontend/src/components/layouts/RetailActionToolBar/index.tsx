import VFButton from "../../../components/VectorFLOW/commons/VFButton";
import { SCVerticalDivider } from "../../../components/VectorFLOW/commons/DailyDataGraphModal/styles";
// import { useUserData } from "../../../context";
import { CheckboxConatiner, CheckboxWrapper, DropDownContainer,ActionableConatiner,ShowAllWrapper, ButtonWrapper } from "./styles"
import { SCViewBackground, SCViewContainer, SCViewImage } from "../../../VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/Planning/ActionToolBar/styles";
import Select from 'react-select'


const Options = [
   {label:'Submit',value:'submit'},
   {label:'Accept',value:'accept'},
]



interface RetailActionToolBarProps {
   themeUi:string,
   onViewChange: (view: string) => void;
   view: string;
   onCallBack:any
   handleSelectChange:any
   handleGoButton:any
   currentStatus:string
   handleOnCancel:any

}


const RetailActionToolBar = ({themeUi, onViewChange, onCallBack,view,handleSelectChange,handleGoButton, currentStatus,handleOnCancel}:RetailActionToolBarProps) =>{



   return (
   <>
    {view === "grid" && (
   <div style={{ display:'flex', alignItems:'center', backgroundColor:'white', marginLeft:'23px', height:'80px', zoom:'0.8'}}>
   <CheckboxWrapper>
       <CheckboxConatiner>
         <input type="checkbox" style={{ zoom: 1.4, accentColor:'white' }}></input>
      </CheckboxConatiner>
      <DropDownContainer>
       <p style={{fontSize:'12px'}}>Select All For Action</p>
         <Select options={Options} placeholder={""} defaultValue={Options[0]} onChange={handleSelectChange}
         styles={{        
            option: (baseStyles, { isSelected }) => ({
               ...baseStyles,
               backgroundColor: isSelected ?themeUi==="REGALBLAZE"?"#FCA311": "#BC3D80" : "white", 
               "&:hover": {
                     backgroundColor:themeUi==="REGALBLAZE"?"rgb(252, 163, 17,0.3) ": '#bc3d814d',
                     color:"black",
               }
            }),
            control: (baseStyles, { isFocused }) => (
               {
                  ...baseStyles, 
                  borderColor: isFocused ? "none": "hsl(0, 0%, 80%);",
                  width: '130px',
                  height:'10px',
                  border: "none",
                  // borderBottom: error ? "3px solid #D03E3E;" : menuIsOpen || isFocused ? '3px solid #820F4C' : '3px solid #A1A1A1',
                  boxShadow: 'none',
                  "&:hover":{
                     borderColor: isFocused ? "none": "hsl(0, 0%, 80%);",
                  }
               }),
         }}
         />
     </DropDownContainer>
   </CheckboxWrapper>
 
     <img
       style={{ cursor: "pointer", marginLeft:'20px'}}
       src={
         themeUi === "REGALBLAZE"
           ? "/assets/img/Group 627-regal.svg"
           : "/assets/img/Group 627.svg"
       }
       height={50.02}
       width={76.83}
       onClick={handleGoButton}
       />
 
   <SCVerticalDivider />

   <ActionableConatiner>
      <ShowAllWrapper >
         <CheckboxConatiner>
            <input type="checkbox" style={{ zoom: 1.5, accentColor:themeUi === "REGALBLAZE" ? "#FCA311" : "#bc3d81" }} onClick={onCallBack}></input>
      </CheckboxConatiner>
         <p style={{fontSize:'16px', fontWeight:'500'}}>Show All</p>
      </ShowAllWrapper>

      <ShowAllWrapper style={{paddingLeft:'10px'}}>
         <CheckboxConatiner>
            <input type="checkbox" style={{ zoom: 1.5, accentColor:themeUi === "REGALBLAZE" ? "#FCA311" : "#bc3d81" }} onClick={onCallBack}></input>
      </CheckboxConatiner>
         <p style={{fontSize:'16px', fontWeight:'500'}}>Show Actionable</p>
      </ShowAllWrapper>
   </ActionableConatiner>
   
{currentStatus === 'Save' ? (
  <ButtonWrapper>
   <button style={{backgroundColor:'white', height:'50px', width:'100px', fontSize:'20px', fontWeight:500, marginRight:'20px'}} onClick={handleOnCancel}>Cancel</button>
      <VFButton onClick={() => console.log('')} themeUi={''} disabled={false}>Save Options</VFButton>
  <SCVerticalDivider />
  <SCViewBackground style={{zoom:'0.8'}} >
     <SCViewContainer>
        <SCViewImage
            src={
              themeUi === "REGALBLAZE"
                ? "/assets/img/VectorFLOW/BPR/chart-view-regal.svg"
                : "/assets/img/VectorFLOW/BPR/chart-view-pink.svg"
            }
           alt=""
        />
        <p style={{color: themeUi === "REGALBLAZE" ? "#FCA311" : "#bc3d81", }}>Chart View</p>
     </SCViewContainer>
     <div>  
        <SCVerticalDivider />
     </div>
        <SCViewContainer onClick={() => {onViewChange("grid")}}>
           <SCViewImage
              src={"/assets/img/VectorFLOW/BPR/grid-view-grey.svg"}
              alt=""
           />
           <p style={{ color: "#b0acac" }}>Grid View</p>
        </SCViewContainer>
      </SCViewBackground>   
   </ButtonWrapper> 
   ) : currentStatus === 'Edit' ? (
      <ButtonWrapper>
        <VFButton onClick={() => console.log('')} themeUi={''} disabled={false}>
          Edit Options
        </VFButton>
        <SCVerticalDivider />
        <SCViewBackground style={{ zoom: '0.8' }}>
          <SCViewContainer>
            <SCViewImage
              src={
                themeUi === "REGALBLAZE"
                  ? "/assets/img/VectorFLOW/BPR/chart-view-regal.svg"
                  : "/assets/img/VectorFLOW/BPR/chart-view-pink.svg"
              }
              alt=""
            />
            <p style={{ color: themeUi === "REGALBLAZE" ? "#FCA311" : "#bc3d81" }}>
              Chart View
            </p>
          </SCViewContainer>
          <div>
            <SCVerticalDivider />
          </div>
          <SCViewContainer onClick={() => onViewChange("grid")}>
            <SCViewImage
              src={"/assets/img/VectorFLOW/BPR/grid-view-grey.svg"}
              alt=""
            />
            <p style={{ color: "#b0acac" }}>Grid View</p>
          </SCViewContainer>
        </SCViewBackground>
      </ButtonWrapper>
    ) : (
      <ButtonWrapper>
        <SCViewBackground style={{ zoom: '0.8' }}>
          <SCViewContainer>
            <SCViewImage
              src={
                themeUi === "REGALBLAZE"
                  ? "/assets/img/VectorFLOW/BPR/chart-view-regal.svg"
                  : "/assets/img/VectorFLOW/BPR/chart-view-pink.svg"
              }
              alt=""
            />
            <p style={{ color: themeUi === "REGALBLAZE" ? "#FCA311" : "#bc3d81" }}>
              Chart View
            </p>
          </SCViewContainer>
          <div>
            <SCVerticalDivider />
          </div>
          <SCViewContainer onClick={() => onViewChange("grid")}>
            <SCViewImage
              src={"/assets/img/VectorFLOW/BPR/grid-view-grey.svg"}
              alt=""
            />
            <p style={{ color: "#b0acac" }}>Grid View</p>
          </SCViewContainer>
        </SCViewBackground>
      </ButtonWrapper>
    )}
   </div> 
   )}  
   </> 
)}

export default RetailActionToolBar
