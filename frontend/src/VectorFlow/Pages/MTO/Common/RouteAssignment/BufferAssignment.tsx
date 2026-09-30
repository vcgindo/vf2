import React from 'react'
import RadioSelect from '../../../../../components/VectorFLOW/commons/MTO/RadioSelect'
import { StepGroup, StepLabel, StepperWrapper } from './RouteAssignment.styled'

const BufferAssignment = ({theme, bufferMaster, selectedBuffers ,setSelectedBuffers, isEditable}: any) => {
  const onValueChange = (newValue: any, type: any) => {
    const buffers = [...selectedBuffers]
    if(type==="prod"){
      buffers[0] = newValue
    }
    else if(type==="proc"){
      buffers[1] = newValue
    }
    setSelectedBuffers(buffers)
  }

  return (
    <StepperWrapper key="buffer-assignment" className="buffer-assignment">
        <StepGroup $step={false} key={`buffer-assignment-1`} style={{width:"100%"}}>
            <StepLabel>Production Buffer</StepLabel>
            <RadioSelect 
              key={`buffer-assignment-1-1`}
              isDisabled={!isEditable}
              theme={theme} 
              options={bufferMaster?.prodMaster}
              value={selectedBuffers[0] || null}
              isClearable
              onChange={(newValue: any) => onValueChange(newValue, "prod")}
              getOptionLabel={(option: any)=>{return `${option.label} - [${option.size}d]`}}
            />
        </StepGroup>
        <StepGroup $step={false} key={`buffer-assignment-2`} style={{width:"100%"}}> 
            <StepLabel>Procurement Buffer</StepLabel>
            <RadioSelect 
              key={`buffer-assignment-2-1`}
              isDisabled={!isEditable}
              theme={theme} 
              isClearable
              options={bufferMaster?.procMaster}
              value={selectedBuffers[1] || null}
              onChange={(newValue: any) => onValueChange(newValue, "proc")}
              getOptionLabel={(option: any)=>{return `${option.label} - [${option.size}d]`}}
            />
        </StepGroup>
    </StepperWrapper>
  )
}

export default BufferAssignment