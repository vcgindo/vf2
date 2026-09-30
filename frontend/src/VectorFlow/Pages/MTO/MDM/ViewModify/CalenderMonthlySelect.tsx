import styled from 'styled-components'

const MonthlyWrapper = styled.div`
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 20px;
`

const Select = styled.select`
width: 100%;
padding: 8px;
font-size: 14px;
border: 1px solid #ddd;
border-radius: 4px;
margin-bottom: 20px;
`;

const AddButton = styled.button`
  background-color: #82104C;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;

  &:hover {
    background-color: #A42C68;
  }
`;

function CalenderMonthlySelect({formData,handleMnOptionsChange,handleMdOptionsChange,onAddClick,onRemoveClick,id}:any) {


  return (
    <MonthlyWrapper>
            <label htmlFor="the" style={{display:"flex",justifyContent:"center", alignItems:"center", fontSize:"1.2rem"}}>
              <input type="radio" id="the" checked /> The
            </label>
            <Select value={formData.dow.filter((month:any)=> month.id === id)[0].mn} onChange={(e)=>handleMnOptionsChange(e,id)} style={{width:"auto", marginBottom:"0px"}}>
            <option value="" selected disabled hidden>Select an option</option>
            {["first","second","third","fourth","last"].map(
              (option, index) => (
                <option key={index} value={option} >
                  {option}
                </option>
              )
            )}
          </Select>
          <Select value={formData.dow.filter((month:any)=> month.id === id)[0].md} onChange={(e)=>handleMdOptionsChange(e,id)} style={{width:"auto",marginBottom:"0px"}}>
          <option value="" selected disabled hidden>Select an option</option>
            {["day","weekday","weekend day","Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map(
              (option, index) => (
                <option key={index} value={option} >
                  {option}
                </option>
              )
            )}
          </Select>
          {id !== 0 ? <AddButton onClick={()=>onRemoveClick(id)}>x</AddButton> : <AddButton onClick={onAddClick}>+</AddButton>}
          
          </MonthlyWrapper>
  )
}

export default CalenderMonthlySelect