import React, { useCallback, useEffect, useMemo, useState } from 'react'
import VFModalCard from '../../../../../components/VectorFLOW/commons/VFModalCard';
import CustomCalenderCaption from "../../../MTA/InsightsAndTrends/ResearchInsights/CustomCalenderCaption";
import moment from 'moment';
import DatePickForm from './DatePickForm';
import { CalenderHeading } from "../../../../../VectorFlow/Pages/MTO/Poogi/InsightAndTrends/ResourceUtilization/styles";
import { CalenderWrapper } from "../../../MTA/InsightsAndTrends/ResearchInsights/styles";
import CustomCalenderDay from '../../Poogi/InsightAndTrends/ResourceUtilization/CustomCalenderDay';
import { DayPicker } from "react-day-picker";


function CalenderModalCard({selectedData, setSelectedData, isModalOpen, setIsModalOpen, onSaveHandler, plantNames, ccrNames, calendarFormData}:any) {

    
    const [maxFol,setMaxFol] = useState<any>(null)
    
    const [highlightedDates, setHighlightedDates] = useState<string[]>([]) 
    const [disableDates,setDisableDates] = useState<any>([])

    // Mapping days to their respective index in JavaScript's Date object (0 for Sunday, 6 for Saturday)
    const dayMap: Record<string, number> = {
    Su: 0,
    Mo: 1,
    Tu: 2,
    We: 3,
    Th: 4,
    Fr: 5,
    Sa: 6,
    };
    
    // Function to generate highlighted dates, memoized using useCallback
    const generateHighlightedDates = useCallback(() => {
      if (!selectedData?.sd || !selectedData?.ed) return [];
    
      const startDate = moment(selectedData.sd, "YYYY-MM-DD");
      const endDate = moment(selectedData.ed, "YYYY-MM-DD");
      const result: string[] = [];
    
      if (selectedData.rb === "Once" || !selectedData.rb) {
        // Highlighted entire range for "Once"
        const current = startDate.clone();
        while (current.isSameOrBefore(endDate)) {
          result.push(current.format("YYYY-MM-DD"));
          current.add(1, "day");
        }
        return result;
      }
    
      // Monthly recurrence
      if (selectedData.rb === "Monthly") {
        selectedData.dow.forEach((day: any) => {
          const currentMonth = moment(startDate).startOf("month");
          while (currentMonth.isSameOrBefore(endDate, "month")) {
            const matchingDate = getNthOccurrenceOfDay(
              currentMonth.year(),
              currentMonth.month(),
              day.mn,
              day.md
            );
    
            if (matchingDate && matchingDate.isBetween(startDate, endDate, "day", "[]")) {
              result.push(matchingDate.format("YYYY-MM-DD"));
            }
            currentMonth.add(1, "month");
          }
        });
        return result;
      }
    
      // Weekly/default logic
      while (startDate.isSameOrBefore(endDate)) {
        const dayOfWeek = startDate.day();
        const selectedDays = selectedData.dow.map((day: any) => day.md);
    
        if (
          (selectedDays.length === 1 && selectedDays.includes("")) ||
          selectedDays.some((day: any) => dayMap[day] === dayOfWeek)
        ) {
          result.push(startDate.format("YYYY-MM-DD"));
        }
        dayOfWeek === 6
          ? startDate.add(selectedData.rd * 7 + 1, "days")
          : startDate.add(1, "day");
      }
      return result;
    }, [selectedData]);
    
    
    const getNthOccurrenceOfDay = (year: number, month: number, occurrence: string, dayType: string) => {
      const firstDayOfMonth = moment({ year, month, day: 1 });
      const lastDayOfMonth = moment({ year, month }).endOf("month");
    
      // If "md" is "day", return the exact nth day of the month
      if (dayType === "day") {
        let dayNumber = 1;
        if (occurrence === "second") dayNumber = 2;
        if (occurrence === "third") dayNumber = 3;
        if (occurrence === "fourth") dayNumber = 4;
        if (occurrence === "last") dayNumber = lastDayOfMonth.date();
    
        const specificDate = moment({ year, month, day: dayNumber });
    
        // Ensure the date falls within the valid range
        return specificDate.isValid() ? specificDate : null;
      }
    
      // Handle weekday/weekend/specific day logic as before
      const dates: moment.Moment[] = [];
      for (let d = moment(firstDayOfMonth); d.isSameOrBefore(lastDayOfMonth); d.add(1, "day")) {
        const weekday = d.isoWeekday();
        const dayOfWeek = d.day();
    
        if (
          (dayType === "weekday" && weekday <= 5) ||
          (dayType === "weekend day" && weekday >= 6) ||
          (dayType in dayMap && dayOfWeek === dayMap[dayType])
        ) {
          dates.push(moment(d));
        }
      }
    
      // Get required occurrence for weekdays/weekends
      if (occurrence === "first") return dates[0];
      if (occurrence === "second") return dates[1];
      if (occurrence === "third") return dates[2];
      if (occurrence === "fourth") return dates[3];
      if (occurrence === "last") return dates[dates.length - 1];
    
      return null;
    };
    
    
    // Memoize the result so it's only recomputed when necessary
    const getHighlightedDates = useMemo(() => generateHighlightedDates(), [generateHighlightedDates]);
    
    
    // Update the state when highlightedDates changes
  useEffect(() => {
    setHighlightedDates(getHighlightedDates);
    }, [getHighlightedDates]);


  const disableTillMaxFol = (isEditMode: boolean, start: string, end: string) => {
    const today = moment().startOf("day");
    const maxDate = moment(maxFol);

    const startDate = moment().startOf("month"); 

    const dates: string[] = [];
    const d = startDate.clone();
  
  
    // Case 1: Edit mode & end date < today
    if (isEditMode && moment(end, "YYYY-MM-DD").isBefore(today, "day")) {  
      const startMoment = moment(start, "YYYY-MM-DD");
      const endMoment = moment(end, "YYYY-MM-DD");
      while (d.isSameOrBefore(maxDate)) {
        if (d.isBefore(startMoment, "day") || d.isAfter(endMoment, "day")) {
          dates.push(d.format("YYYY-MM-DD"));
        }
        d.add(1, "day");
      }
    }
  
    // Case 2: Edit mode & end date > today
    else if (isEditMode && moment(end, "YYYY-MM-DD").isAfter(today, "day")) {
      while (d.isSameOrBefore(maxDate)) {
        dates.push(d.format("YYYY-MM-DD")); // pura FOL kiya maine grey out
        d.add(1, "day");
      }
      }
    
    // Case 3: Add mode (normal FOL calculation)
    else {  
      while (d.isSameOrBefore(maxDate)) {
        dates.push(d.format("YYYY-MM-DD")); // pura FOL grey out
        d.add(1, "day");
      }
    }
  
    return dates;
  };
  
  
  useEffect(() => { 
    if (selectedData?.ccr_id?.length === 0) {
      // setMaxFol(null);
      setDisableDates([]);
      setHighlightedDates([]);
      setSelectedData((prev: any) => ({
        ...prev,
        sd: "",
        ed: "",
      }));
      return;
    }
  
    let dates:any = [];
  
    // Edit mode case: if end date < today
    if ( (selectedData?.ed && new Date(selectedData.ed) < new Date())) {
      dates = DisableEndDateToTodayDate(); 
    } else {
      // Normal case: disable based on FOL calculation
      dates = disableTillMaxFol(true, selectedData?.sd || "", selectedData?.ed || "");
    }
    setDisableDates(dates);

  }, [selectedData?.ccr_id, selectedData?.ed, maxFol]);
      
    // to update the left side of the calender to max of maxFol and startdate
    const safeMaxDate = useMemo(() => {
      const datesToCompare :any= [
        moment(maxFol, "YYYY-MM-DD").add(1,'day'),
        selectedData?.sd ? moment(selectedData.sd, "YYYY-MM-DD").add(1,'day') : null,
      ].filter((m) => m && m.isValid());
      
      return datesToCompare.length > 0
      ? moment.max(datesToCompare).toDate()
      : new Date();
    }, [maxFol, selectedData?.sd]);

    const [visibleMonth, setVisibleMonth] = useState<Date>(safeMaxDate);
    
  useEffect(() => {
    if (selectedData?.sd) { 
      setVisibleMonth(safeMaxDate);
    }
    }, [selectedData?.sd]);
    
  const minAllowedMonth = useMemo(() => {
    const today = moment().startOf("month").toDate();
    if (selectedData?.sd) {
      const startDate = moment(selectedData.sd, "YYYY-MM-DD").startOf("month").toDate(); 
      return startDate < today ? startDate : today;
    }
      return today;
    },[selectedData.sd]);

  
    const DisableEndDateToTodayDate = () => {
      const start = selectedData?.sd;
      const end = selectedData?.ed;
      if (!start || !end) return [];
    
      const startDate = moment(start, "YYYY-MM-DD").startOf("day");
      const endDate = moment(end, "YYYY-MM-DD").startOf("day");
    
      // Choose a very large range so we cover all possible dates in the calendar
      const minDate = startDate.clone().subtract(10, "years");
      const maxDate = endDate.clone().add(10, "years");
    
      const dates: string[] = [];
    
      const current = minDate.clone();
      while (current.isSameOrBefore(maxDate)) {
        // Grey out everything exccpet the start-end range
        if (!(current.isSameOrAfter(startDate) && current.isSameOrBefore(endDate))) {
          dates.push(current.format("YYYY-MM-DD"));
        }
        current.add(1, "day");
      }
    
      return dates;
    };

  // console.log(disableDates, 'Disable dates')
        
  return (
    <VFModalCard
    openModal={isModalOpen}
    closeModal={() => {
      setIsModalOpen(false);
    }}
    headerText={"Add Details"}
    headerIcon={""}
    closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}
  >
    <div
      style={{
        height: "76vh",
        width: "72vw",
        overflowX: "hidden",
        background: "#f4f4f4",
      }}
    >
      <div
        style={{
          height: "100%",
          display: "flex",
          justifyContent: "space-around",
        }}
      >
        <div>
          <div
            style={{
              padding: "10px",
              width: "100%",
              margin: "50px 0 20px 20px",
            }}
          >
            <CalenderWrapper
              style={{
                zoom: "1",
                background: "white",
                borderRadius: "12px",
              }}
            >
              <CalenderHeading
                style={{ width: "100%", fontWeight: "bold" }}
                data-testid="utilization"
              >
                Calendar
              </CalenderHeading>
              <DayPicker
                style={{
                  display: "flex",
                  justifyContent: "center",
                }}
                  defaultMonth={safeMaxDate}
                month={visibleMonth}
                onMonthChange={setVisibleMonth}
                  // fromMonth={new Date()}
                  fromMonth={minAllowedMonth}
                  mode="single"
                components={{
                  Caption: CustomCalenderCaption,
                  Day: (props:any) => {
                    const formattedDate = moment(props?.date).format(
                      "YYYY-MM-DD"
                    );
                    const color = highlightedDates?.includes(formattedDate)
                      ? "selected"
                      : disableDates?.includes(formattedDate) ? "disabled" : "default";

                    const opacity :string = disableDates?.includes(formattedDate) ? "0.6" : "1"
                    return <CustomCalenderDay {...props} color={color} opacity={opacity}
                    />;
                  },
                }}
                styles={{
                  cell: {
                    padding: "5px",
                  },
                }}
              />
            </CalenderWrapper>
          </div>
        </div>
        <div
          style={{
            height: "90%",
            borderLeft: "2px solid #A0A0A0",
            margin: "40px 0",
          }}
        ></div>
        <div >
          {
            <DatePickForm
              plantNames={plantNames}
              calendarFormData={calendarFormData}
              ccrNames={ccrNames}
              formData={selectedData}
              setFormData={setSelectedData}
              onSaveHandler={onSaveHandler}
              setIsModalOpen={setIsModalOpen}
              setMaxFol={setMaxFol}
              maxFol={maxFol}
            />
          }
        </div>
      </div>
    </div>
  </VFModalCard>
  )
}

export default CalenderModalCard