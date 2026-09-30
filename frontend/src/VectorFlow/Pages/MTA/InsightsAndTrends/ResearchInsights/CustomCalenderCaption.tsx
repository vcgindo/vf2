import {CaptionProps,useNavigation} from 'react-day-picker'

import {format} from 'date-fns'

import { CustomCalenderCaptionArrow, CustomCalenderCaptionHeader, CustomCalenderCaptionWrapper } from "./styles"



const CustomCalenderCaption = (props:CaptionProps)=>{

    const {nextMonth,previousMonth,goToMonth} = useNavigation()

    return(
        <CustomCalenderCaptionWrapper>
            <CustomCalenderCaptionArrow style={{transform:'rotate(90deg)'}} src='/assets/img/VectorFLOW/BPR/calender-left-arrow.svg' onClick={()=>previousMonth && goToMonth(previousMonth)}/>
            <CustomCalenderCaptionHeader>
                {format(props.displayMonth,'MMM yyy')}
            </CustomCalenderCaptionHeader>
            <CustomCalenderCaptionArrow  style={{transform:'rotate(90deg)'}} src='/assets/img/VectorFLOW/BPR/calender-right-arrow.svg' onClick={()=>nextMonth && goToMonth(nextMonth)}/>
        </CustomCalenderCaptionWrapper>
    )
}

export default CustomCalenderCaption