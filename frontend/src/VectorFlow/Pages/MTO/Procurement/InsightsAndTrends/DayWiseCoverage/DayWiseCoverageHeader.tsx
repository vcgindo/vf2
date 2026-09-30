import { useEffect, useState } from 'react'
//import { useUserData } from '../../../../../../context'
import DatePicker from '../../../../../../components/VectorFLOW/commons/MTO/DatePicker'
import { DayWiseCoverageHeaderContainer, DayWiseCoverageStatus, Divider, Text } from './style'
import { format } from 'date-fns'
import { useUserData } from '../../../../../../context'
import VFButton from '../../../../../../components/VectorFLOW/commons/VFButton'

interface IDayWiseCoverageHeaderProps {
    startDate: string,
    endDate: string,
    setDateRange: (start: string, end: string) => void,
    max: Date,
    min: Date,
}

const DayWiseCoverageHeader = ({
    startDate,
    endDate,
    setDateRange,
    max,
    min
}: IDayWiseCoverageHeaderProps) => {
    //const { user } = useUserData();
    //const themeUi = user?.user?.theme_ui;
    const [start, setStart] = useState(startDate);
    const [end, setEnd] = useState(endDate);

    const [minEndDate, setMinEndDate] = useState(format(min, "yyyy-MM"));
    const [maxStartDate, setMaxStartDate] = useState(format(max, "yyyy-MM"))


    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;    

    useEffect(() => {
        if (!(start.length && end.length)) {
            setIsDisabled(true)
        }
        else {
            setIsDisabled(false)
        }
        if (start && start.length) {

            setMinEndDate(start)
        }
    }, [start])

    useEffect(() => {
        if (!(start.length && end.length)) {
            setIsDisabled(true)
        }
        else {
            setIsDisabled(false)
        }
        if (end && end.length !== 0) {

            setMaxStartDate(end)
        }

    }, [end])


    const [isDisabled, setIsDisabled] = useState(false);

    return (
        <DayWiseCoverageHeaderContainer>
            <DayWiseCoverageStatus color={"#33800B"}>
                Full Kit Available
            </DayWiseCoverageStatus>
            <DayWiseCoverageStatus color={"#E53F3F"}>
                Partial/ No Kit Available
            </DayWiseCoverageStatus>
            <Divider />
            <Text>From</Text>
            <DatePicker type="month" date={start} setDate={setStart} data-testid="start" min={format(min, "yyyy-MM")} max={format(maxStartDate, "yyyy-MM")} />
            <Text>To</Text>
            <DatePicker type="month" date={end} setDate={setEnd} data-testid="end" min={format(minEndDate, "yyyy-MM")} max={format(max, "yyyy-MM")} />
            {/* <div style={{ display: 'flex', alignItems: 'center' }}> */}
            {/* <img
                style={{ cursor: 'pointer', opacity: isDisabled ? '0.7' : '1' }}
                src={themeUi === "REGALBLAZE" ? "/assets/img/Group 627-regal.svg" : "/assets/img/Group 627.svg"}
                height={50}
                width={60}
                alt={"Submit"}
                onClick={() => { (!isDisabled) && setDateRange(start, end) }}
            /> */}
            <VFButton
          onClick={() => {
            !isDisabled && setDateRange(start, end);
          }}
          themeUi={themeUi}
          disabled={false}
          style={{
            // cursor: isSaveButtonEnabled ? "pointer" : "not-allowed",

            height: "43px",
            width: "59px",
            borderRadius: "3px",
            // opacity: isSaveButtonEnabled ? 1 : 0.5, // Visual cue for disabled
            // pointerEvents: isSaveButtonEnabled ? "auto" : "none", // Prevent click when disabled
          }}
        >
          <img
            src="/assets/img/rightArrowHorizontal.svg"
            height={13}
            width={7}
          />
        </VFButton>

            {/* </div> */}
        </DayWiseCoverageHeaderContainer>
    )
}

export default DayWiseCoverageHeader