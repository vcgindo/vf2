// VFRangeSlider.tsx
import React, { useState } from 'react';
import { useUserData } from '../../../../../context';
import { RangeSliderContainer, RangeSliderInput, ValueLabel, ToolTipTriangle } from './styles';

interface VFRangeSliderProps {
    milestones?: number[];
    min: number
    max: number
    strictMode: boolean
    width: number
    defaultValue: number
    showTriangle: boolean
    handleChange: (number: number) => void
    labelValueFormatter?: (number: number) => string
    style?: any
}


const VFRangeSlider: React.FC<VFRangeSliderProps> = ({ milestones, min, max, strictMode, width, defaultValue, showTriangle, handleChange, labelValueFormatter, style }) => {
    const [value, setValue] = useState<number>(defaultValue);
    const [currMileStoneIndex, setCurrMileStoneIndex] = useState<number>(0)

    const { user } = useUserData()
    const themeUi = user.user.theme_ui
    const range = max - min
    const multiplier = width - 20


    const handleSliderChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const currValue = parseInt(event.target.value)
        if (strictMode && milestones) {
            if (currValue < milestones[currMileStoneIndex] && currMileStoneIndex > 0 && currValue < (milestones[currMileStoneIndex] + milestones[currMileStoneIndex - 1]) / 2) {
                setCurrMileStoneIndex(currMileStoneIndex - 1)
                setValue(milestones[currMileStoneIndex - 1])
                handleChange(milestones[currMileStoneIndex - 1])
                return
            }
            if (currValue > milestones[currMileStoneIndex] && currMileStoneIndex < milestones.length && currValue > (milestones[currMileStoneIndex + 1] + milestones[currMileStoneIndex]) / 2) {
                setCurrMileStoneIndex(currMileStoneIndex + 1)
                setValue(milestones[currMileStoneIndex + 1])
                handleChange(milestones[currMileStoneIndex + 1])
                return
            }


        }
        else {
            setValue(currValue);
            handleChange(currValue)
        }
    };

    const valueFormatter = () => {
        if (!labelValueFormatter) return value
        return labelValueFormatter(value)
    }


    return (
        <RangeSliderContainer style={{ width, ...style }}>

            <RangeSliderInput
                theme={themeUi}
                type="range"
                data-testid="range-slider"
                min={min}
                max={max}
                value={value}
                onChange={handleSliderChange}
                progressValue={(value / max) * 100}
            />
            {/* <RangeProgress 
            style={{width:value===0?0:((value / range) * multiplier) + 6}}
        /> */}
            {/* <RangeProgressBackground/> */}
            <ValueLabel style={{ borderRadius: '50%', fontWeight: 'bold' }} left={((value / range) * multiplier) - 3} top={showTriangle ? 32 : 30}>{valueFormatter()}</ValueLabel>
            {showTriangle && (
                <ToolTipTriangle
                    style={{ left: ((value / range) * multiplier) + 6.5 }}
                />
            )}
            <div style={{width: "100%", margin:"0 2px", display:"flex", justifyContent:"space-between", padding:"12px 3px", position:"absolute"}}>
                <strong>
                    {min}
                </strong>
                <strong>
                    {max}
                </strong>
            </div>
            {/* {milestones && (
                <MilestonesContainer>
                    {milestones.map((milestone: number, index: number) => {
                        if (milestone !== milestones[currMileStoneIndex]) {
                            return <MilestoneLabel style={{ left: ((milestone / range) * multiplier) + 6.5, top: !showTriangle ? -7 : 6 }} key={index}>{milestone}</MilestoneLabel>
                        }
                    })}
                </MilestonesContainer>
            )} */}
        </RangeSliderContainer>
    );
};

export default VFRangeSlider;
