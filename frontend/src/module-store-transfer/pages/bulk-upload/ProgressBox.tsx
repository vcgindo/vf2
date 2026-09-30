import React from 'react'
import { LabelText, ProgressBoxWrapper } from './style'
import CircularProgress from './CircularProgress'

interface ProgressBoxProps {
    label : string;
    progress: number;
}

function ProgressBox({label, progress} : ProgressBoxProps) {
  return (
    <ProgressBoxWrapper>
        <CircularProgress size={120} progress={progress} />
        <LabelText>{label}</LabelText>
    </ProgressBoxWrapper>
  )
}

export default ProgressBox