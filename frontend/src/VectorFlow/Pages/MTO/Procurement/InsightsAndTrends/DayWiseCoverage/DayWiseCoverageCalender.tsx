import _ from 'lodash'
import React, { Dispatch, SetStateAction } from 'react'
import { CalenderContainer, CalenderContent, CalenderMonth, CalenderMonths, CalenderTitle, Day, Month, Calender } from './style'
import { eachMonthOfInterval, format, getDaysInMonth, getYear } from 'date-fns'
import Tooltip from '../../../../../../components/VectorFLOW/commons/MTO/Tooltip'

interface IDayWiseCoverageCalenderProps {
    start: string,
    end: string,
    getToolTipContent: (id: string) => JSX.Element | null,
    getColor: (id: string) => string,
    selectedDate: string,
    setSelectedDate: Dispatch<SetStateAction<string>>,
}

const DayWiseCoverageCalender = ({
    start,
    end,
    getToolTipContent,
    getColor,
    selectedDate,
    setSelectedDate
}: IDayWiseCoverageCalenderProps) => {

    const getMonths = (start: string, end: string) => {
        const monthRange = eachMonthOfInterval({ start: new Date(start), end: new Date(end) });
        const years = new Set();
        monthRange.forEach((date: any)=>{
            years.add(getYear(date));
        })
        return (
            <CalenderContainer>
                <CalenderTitle>Calender {Array.from(years).join("/")}</CalenderTitle>
                <CalenderContent>
                    <CalenderMonths>
                        {monthRange.map((month: any) => {
                            return (
                                <CalenderMonth>
                                    {format(month, "MMM")}
                                </CalenderMonth>
                            )
                        })}

                    </CalenderMonths>

                    <Calender>
                        <tbody>
                            {monthRange.map((month: any, index: number) => {
                                return (
                                    <Month key={index}>
                                        {_.range(0, getDaysInMonth(month)).map((day: number, index) => {
                                            const formattedDate = format(`${month.getFullYear()}/${month.getMonth() + 1}/${day + 1}`, "yyyy-MM-dd");
                                            const content = getToolTipContent(formattedDate)
                                            return (
                                                <Day style={{opacity: (selectedDate == "" || selectedDate === formattedDate) ? "1"  : "0.5", cursor: !content ? "not-allowed" :"pointer"}} key={index} color={getColor(formattedDate)} onClick={() => selectedDate === formattedDate ? setSelectedDate("") : setSelectedDate(formattedDate)}>
                                                    {content ? <Tooltip content={content}>
                                                        {day + 1}
                                                    </Tooltip> : day + 1 }
                                                    
                                                </Day>
                                            )
                                        })}

                                    </Month>
                                )
                            })}
                        </tbody>
                    </Calender>
                </CalenderContent>

            </CalenderContainer>
        )
    }

    return (
        <div>
            {getMonths(start, end)}
        </div>
    )
}

export default DayWiseCoverageCalender