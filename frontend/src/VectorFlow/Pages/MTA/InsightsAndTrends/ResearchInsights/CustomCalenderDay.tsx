import { format, isSameMonth } from 'date-fns'
import { DayProps, useNavigation } from 'react-day-picker'
import { BPRColorMapper } from '../../../../../helpers/utils'
import { CustomCalenderDayWrapper } from './styles'


interface CustomCalenderDayProps extends DayProps {
    color: string
}



const CustomCalenderDay = (props: CustomCalenderDayProps) => {

    const { currentMonth } = useNavigation()


    const isDateValid = isSameMonth(currentMonth, props.date)
    const currColors = BPRColorMapper(props.color)

    if (isDateValid) {
        return (
            <CustomCalenderDayWrapper style={{
                backgroundColor: currColors.bg,
                color: currColors.text
            }}>
                {format(props.date, 'dd')}
            </CustomCalenderDayWrapper>
        )
    }
    return <></>
}


export default CustomCalenderDay