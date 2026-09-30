import styled from "styled-components";
import { useUserData } from '../../../../../context'
import { useEffect, useState} from "react";
import CalenderMonthlySelect from "./CalenderMonthlySelect";
import _ from "lodash"
import { SCFlexCenter, SCItemMulSelect, SCSwapItem } from "../../../../../components/layouts/ProductPermission/styles";
import { SearchInputMultiple } from "../../../../../components";
import moment from "moment";
import { useGetMaxFolDate } from "../../../../../VectorFlow/Services/MTA/MDM";



const FormContainer = styled.div`
width: 400px;
position: relative;
padding: 20px;
background-color: #f4f4f4;
border-radius: 8px;
font-family: Arial, sans-serif;
`;

const RadioGroup = styled.div`
display: flex;
align-items: center;
margin-bottom: 20px;
`;

const RadioLabel = styled.label<{theme:string}>`
display: flex;
align-items: center;
margin-right: 20px;
font-size: 14px;
accent-color:${(props)=>props.theme==="REGALBLAZE"?"#C7810E":"#82104C"};

`;

const RadioInput = styled.input`
margin-right: 8px;
`;

const Label = styled.label`
display: block;
margin-bottom: 8px;
font-size: 14px;
color: #666;
`;

const Input = styled.input`
width: 100%;
padding: 8px;
font-size: 14px;
border: 1px solid #ddd;
border-radius: 4px;
margin-bottom: 20px;
`;

const Select = styled.select`
width: 100%;
padding: 8px;
font-size: 14px;
border: 1px solid #ddd;
border-radius: 4px;
margin-bottom: 20px;
`;

const DaysContainer = styled.div`
display: flex;
margin-bottom: 20px;
`;

const Day = styled.button`
flex: 1;
padding: 10px 10px;
font-size: 14px;
border: none;
border-radius: 4px;
background-color:'white';
 color: ${(props:any) => (props?.isSelected ? '#fff' : '#333')}; 
cursor: pointer;
margin-right: 4px;

&.selected{
background: ${(props) => props.theme === "REGALBLAZE" ? "#C7810E" : "#82104C"};
color:white;
} 

&:last-child {
  margin-right: 0;
}

`;
const InputWrapper = styled.div`
display: flex;
gap: 10px;
align-items: center;
justify-content: space-between;
`

const FooterText = styled.p`
font-size: 12px;
color: #7e0044;
text-align: left;
margin-top: -10px;
`;

const DatePickForm=({ plantNames, calendarFormData, ccrNames, formData, setFormData,setIsModalOpen,onSaveHandler,maxFol,setMaxFol}: any)=>{

  const {user} = useUserData()
  const themeUi = user.user.theme_ui
  const isDisabled =  formData.sd === '' || formData.ed === ''
  const [ccrNameOptFromPlant, setCcrNameOptFromPlant] = useState<any>(ccrNames) 

  const { mutateAsync: GetMaxFolDate } = useGetMaxFolDate();
  
  useEffect(() => {
    setFormData((prev: any) => ({
      ...prev,
      ...calendarFormData,
      rb: calendarFormData?.rb || "Once",   
    }));
  }, [calendarFormData]);
  


const onHandleChange=(e:any)=>{
  setFormData({
    ...formData,
    iwd: e.target.value == "holiday" ? false : true
  })
}

const onHandleTitleChange = (e:any)=>{
  setFormData({
    ...formData,
    dsc: e.target.value 
  })
}

  const onHandleOptionChange = (e: any) => {
  setFormData((prevFormData: any) => ({ ...prevFormData, dow: [{ id: 0, mn: "", md: "" }], rd: null, rb: e.target.value || 'Once' }))
    } 
  
const onHandlePlantChange = (e:any)=>{
  const selectedPlantId = Number(e.target.value);
  const filteredCcrNames = ccrNames
    .filter((ccr: any) => ccr.plant === selectedPlantId)
    .map((ccr: any) => ({ value: ccr.ccr_id, label: ccr.ccr_name }));

  setCcrNameOptFromPlant(filteredCcrNames);

  setFormData((prevFormData:any)=>({
    ...prevFormData,
    plid: selectedPlantId,
    plnm:plantNames.find((pl:any)=> pl.plant_id == selectedPlantId)?.plant_name,
    ccr_id: [],
    ccr:"",
  }))
  }
  
const [ccrMapFol, setccrMapFol]=useState<any>()

  const fetchccrMapFol:any = async () => {
    try {
      const FOLData = await GetMaxFolDate();  
      if (FOLData?.data) {
        setccrMapFol( FOLData.data.data)
      }
    } catch (error) {
      console.error("Error fetching FOL date", error);
    }
  };


  useEffect(() => {
    fetchccrMapFol();
  }, [formData?.ccr_id]);
  
  useEffect(() => {
    (ccrMapFol || formData.ccr_id ) 
      setMaxFolFn(formData.ccr_id );    
  },[formData.ccr_id,ccrMapFol])


const onHandleCCRChange = (e:any)=>{
  const ccrIds = e.map((ccr:any)=> ccr.value)
  const ccrNames = e.map((ccr:any)=> ccr.label).join(",")
  setFormData({
    ...formData,
    ccr_id: ccrIds ,
    ccr: ccrNames,
  })
  setMaxFolFn(ccrIds)
}

  const setMaxFolFn = (ccrs: any) => {
    if (!ccrMapFol) {
      return   
    } 
  const dates = []
    const plant = formData.plid
  if(plant in ccrMapFol){
    for(const ccr of ccrs){
      if(ccr in ccrMapFol[plant]){
        dates.push(ccrMapFol[plant][ccr])
      }
    }
    // const momentDates = dates.map(date => moment(date, 'DD/MM/YYYY'));
    const momentDates = dates.map(date => moment(date, ['DD/MM/YYYY', 'YYYY-MM-DD'], true));

    const maxDate = moment.max(momentDates);
    setMaxFol(maxDate.format('YYYY-MM-DD'))
  }
  }

  const onHandleEndDateChange = (e:any) =>{
  setFormData({
    ...formData,
      ed:e.target.value

    })

  }

const onHandleStartDateChange = (e:any) =>{
  setFormData({
    ...formData,
      sd:e.target.value
  
  })
}


const onHandleEVeryChange = (e:any)=>{
  setFormData({
    ...formData,
    rd: Number(e.target.value)

  })
}


const handleAddDow = (day: string) => {


  setFormData((prevFormData: any) => {
    const updatedDow = [...prevFormData.dow];
    if(updatedDow.length === 1 && updatedDow[0].md === ""){
      updatedDow[0] = { id: 0, mn: "", md: day };
    }else if (!updatedDow.some((entry: any) => entry.md === day)) {
      updatedDow.push({ id: updatedDow.length, mn: "", md: day });
    } else {
      const index = updatedDow.findIndex((entry: any) => entry.md === day);
      updatedDow.splice(index, 1);
    }
    return { ...prevFormData, dow: updatedDow };
  })

};

useEffect(() => {

  // Clear all selections first to avoid duplicate toggling issues
  document.querySelectorAll(".selected").forEach((el) => {
    el.classList.remove("selected");
  });

  // Apply the correct class to selected days
 if(formData && formData.dow && Array.isArray(formData.dow)){

   formData?.dow.map((day:any)=> day.md).forEach((day: string) => {
     const element = document.getElementById(day);
     if (element) {
       element.classList.add("selected");
     }
   });
 }
}, [formData.dow]);


  useEffect(() => {
  if(formData.rb !== "Weekly"){
    if(formData?.dow?.length===0){
      setFormData((prevFormData:any)=> ({...prevFormData, dow :[{id:0,mn:"",md:""}], rd:null}))
    }
  }
  else  {
    if(formData?.dow?.length===0){
      setFormData((prevFormData:any)=> ({...prevFormData, dow :[]}))
    }
  }
},[formData.rb])

const handleMnOptionsChange = (e: React.ChangeEvent<HTMLSelectElement>,id:number) => {
  setFormData((prevFormData : any) => (
    { ...prevFormData,
      dow : prevFormData.dow.map((month:any)=> month.id == id ? {...month, mn:e.target.value}: month)
     }
  ));
}

const handleMdOptionsChange = (e: React.ChangeEvent<HTMLSelectElement>,id:number)=>{
  setFormData((prevFormData: any) => (
    {...prevFormData, 
      dow : prevFormData.dow.map((month:any)=> month.id == id ? {...month, md: e.target.value} : month),
    }
  ))
}

// Filter CCR names based on selected plant
useEffect(() => {
  if (formData.plid) {
    const filteredCcrNames = ccrNames
      .filter((ccr: any) => ccr.plant === formData.plid)
      .map((ccr: any) => ({ value: ccr.ccr_id, label: ccr.ccr_name }));
    setCcrNameOptFromPlant(filteredCcrNames);
  }
}, [formData.plid, ccrNames]);


const onAddClick = ()=>{
  const newFormData = _.cloneDeep(formData);
  newFormData.dow.push({id: formData.dow.length, mn: "", md: ""});
  setFormData(newFormData);
}

const onRemoveclick = (id: number) => {
  const newFormData = _.cloneDeep(formData);
  newFormData.dow = newFormData.dow.filter((val:any) => val.id !== id);
  setFormData(newFormData)
  }


  
  const [isFieldDisabled, setIsFieldDisabled] = useState(false);

  useEffect(() => {
    if (!formData.sd) {
      setIsFieldDisabled(false); 
      return;
    }
  
    const today = moment().startOf("day");
    const selectedStart = moment(formData.sd, "YYYY-MM-DD");
  
    if (selectedStart.isBefore(today)) {
      setIsFieldDisabled(true); 
    } else {
      setIsFieldDisabled(false); 
    }
  }, [formData.sd]);

  

  return (
    <>
      <fieldset
    disabled={isFieldDisabled}
    style={{
      border: "none",
      padding: 0,
      margin: 0,
      opacity: isFieldDisabled ? 0.6 : 1,
      pointerEvents: isFieldDisabled ? "none" : "auto"
    }}
  >
      <FormContainer>
        <RadioGroup>
          <RadioLabel theme={themeUi}>
            <RadioInput
              type="radio"
              name="type"
              value="holiday"
              checked={formData.iwd === false}
              onChange={onHandleChange}
            />
            Holiday
          </RadioLabel>
          <RadioLabel>
            <RadioInput
              type="radio"
              name="type"
              value="working"
              checked={formData.iwd === true}
              onChange={onHandleChange}
            />
            Working
          </RadioLabel>
        </RadioGroup>

        <InputWrapper>
          <Label>Title</Label>
          <Input
            type="text"
            placeholder="Add name of holiday"
            value={formData.dsc}
            onChange={onHandleTitleChange}
          />
        </InputWrapper>

        <InputWrapper>
          <Label>Plant</Label>
          <Select value={formData.plant__plant_name || formData.plnm} onChange={onHandlePlantChange}>
            <option value="" selected disabled hidden>
              Select a Plant
            </option>
            {plantNames.map((plant: any, index: number) => (
              <option key={index} value={plant.plant_id}>
                {plant.plant_name}
              </option>
            ))}
          </Select>
        </InputWrapper>

        <InputWrapper style={{marginBottom:'10px'}}>
          <Label>CCR</Label>

          <SCSwapItem key={0}>
            <SCFlexCenter>
              <SCItemMulSelect width={"85%"}>
                <SearchInputMultiple
                  placeholder={"Select CCR"}
                  options={formData.plid ? ccrNameOptFromPlant : []}
                    value={(formData?.ccr_id)?.map((ccr: any) => ({
                    value: ccr,
                    label: ccrNames
                      .find((ccrName: any) => ccrName.ccr_id == ccr)?.ccr_name || "",
                  }))}
                  setValue={onHandleCCRChange}
                  handleListChild={() => {
                    return null;
                  }}
                  disabled={false}
                  key={0}
                />
              </SCItemMulSelect>
            </SCFlexCenter>
          </SCSwapItem>
        </InputWrapper>

        <InputWrapper>
          <Label>Repeat</Label>
          <Select value={formData?.rb || "Once"} onChange={onHandleOptionChange}>
            {["Once", "Weekly", "Monthly"].map((option, index) => (
              <option key={index} value={option}>
                {option}
              </option>
            ))}
          </Select>
        </InputWrapper>

        <InputWrapper>
          <Label>Start</Label>
          <Input
            disabled={formData?.ccr_id?.length === 0 }
            type="date"
            min={moment(maxFol).add(1,'day').format('YYYY-MM-DD')}
            value={formData.sd}
            onChange={onHandleStartDateChange}
          />
        </InputWrapper>

        {formData.rb === "Weekly" && (
          <>
            <InputWrapper>
              <Label>Every</Label>
              <Input
                type="number"
                max="4"
                value={formData?.rd}
                onChange={onHandleEVeryChange}
                // disabled={!(formData.hid == null)}
              />
              Week(s)
            </InputWrapper>
            <InputWrapper>
              <Label>On</Label>
              <DaysContainer>
                {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map(
                  (day: any, index) => (
                    <Day
                      key={index}
                      id={day}
                      onClick={() => {
                        handleAddDow(day);
                      }}
                    >
                      {day}
                    </Day>
                  )
                )}
              </DaysContainer>
            </InputWrapper>
          </>
        )}
        {formData.rb === "Monthly" &&
          formData?.dow?.map((val: any) => {
            return (
              <CalenderMonthlySelect
                key={val.id}
                formData={formData}
                handleMdOptionsChange={handleMdOptionsChange}
                handleMnOptionsChange={handleMnOptionsChange}
                onAddClick={onAddClick}
                onRemoveClick={onRemoveclick}
                id={val.id}
              />
            );
          })}

        
        <InputWrapper>
          <Label>Ends</Label>
          <Input
          disabled={formData?.ccr_id?.length === 0 }
            type="date"
            min={formData.sd ? moment(formData.sd).format('YYYY-MM-DD'): moment(maxFol).add(1,'day').format('YYYY-MM-DD')}
            // defaultValue={}
            value={formData.ed}
            onChange={onHandleEndDateChange}
          />
        </InputWrapper>

        <div style={{ zoom: "0.8", marginTop: "10px" }}>
          <div
            key={"1"}
            style={{
              display: "flex",
              justifyContent: "right",
              gap: "8px",
              borderTop: "2px dashed #A0A0A0",
              padding: "20px 10px 0 0",
            }}
          >
            <div>
              <button
                disabled={isDisabled}
                type="submit"
                onClick={() => {
                  onSaveHandler();
                }}
                style={{
                  font: "normal normal 300 16px/24px Roboto",
                  fontWeight: "400",
                  padding: "10px 30px",
                  color: "white",
                  borderRadius: "6px",
                  background: isDisabled ? "gray" : "#820F4C",
                  boxShadow: "0px 6px 25px #00000029",
                  cursor: isDisabled ? "not-allowed" : "pointer",
                }}
              >
                Save
              </button>
            </div>
            <div>
              <button
                style={{
                  background: "white",
                  color: "grey",
                  font: "normal normal 300 16px/24px Roboto",
                  padding: "10px 20px",
                  fontWeight: "400",
                  borderRadius: "6px",
                  border: "1px solid grey",

                  boxShadow: "0px 6px 25px #00000029",
                }}
                onClick={() => {
                  setIsModalOpen(false);
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
        </FormContainer>
        </fieldset>
      </>
    

    );
}

export default DatePickForm;