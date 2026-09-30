import { format, isSameMonth } from 'date-fns'
import { DayProps, useNavigation } from 'react-day-picker'
import { BPRColorMapper } from '../../../../../../helpers/utils'
import { CustomCalenderDayWrapper } from './styles'


interface CustomCalenderDayProps extends DayProps {
    color: string
    opacity?:string
}



const CustomCalenderDay = (props: CustomCalenderDayProps) => {

    const { currentMonth } = useNavigation()


    const isDateValid = isSameMonth(currentMonth, props.date)
    const currColors = BPRColorMapper(props.color)
    const opacity = props?.opacity


    if (isDateValid) {
        return (
            <CustomCalenderDayWrapper
                data-testid="custom-calender-day"
                style={{
                backgroundColor: currColors.bg,
                color: currColors.text,
                opacity: opacity ? opacity : '1'
            }}>
                {format(props.date, 'dd')}
            </CustomCalenderDayWrapper>
        )
    }
    return <></>
}


export default CustomCalenderDay