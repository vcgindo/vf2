import React from 'react'
import { DateInput, DatePickerContainer } from './styles'

interface IDateProps {
    date: string,
    setDate: (date: string) => void,
    type: "month" | "date",
    min?: string,
    max?: string
}
const DatePicker = ({ date, setDate, type, min, max }: IDateProps) => {
    return (
        <DatePickerContainer data-testid="calender">
            <DateInput

                value={date}
                type={type}
                min={min}
                max={max}

                onChange={(e) => {
                    setDate(e.target.value);
                }}
            />
        </DatePickerContainer>
    )
}

export default DatePicker