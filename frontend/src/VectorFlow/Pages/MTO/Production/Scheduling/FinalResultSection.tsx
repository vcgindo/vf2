import React, { useEffect, useState } from "react";
import SchedulingActionToolbar from "./components/SchedulingActionToolbar";
import ResourceView from "./Sections/ResourceView";
import JobView from "./Sections/JobView";
import GridViewResource from "./Sections/GridViewResource";
import GridViewJob from "./Sections/GridViewJob";
import VFOverlayModal from "../../../../../components/VectorFLOW/commons/VFOverlayModal";
import FilterModal from "./components/FilterModal";
import _ from "lodash";
import { FinalResultSectionWrapper } from "./SchedulingStyles";



const FinalResultSection = ({ setStep, finalResult }: any) => {
  const [excelGridRef, setExcelGridRef] = useState<any>(null);
  const [currentView, setCurrentView] = useState("ResourceView");

  const [data, setData] = useState(finalResult);
  const getCurrentView = () => {
    switch (currentView) {
      case "ResourceView":
        return (
          <ResourceView ResourceData={data} setExcelGridRef={setExcelGridRef} />
        );
      case "JobView":
        return <JobView ResourceData={data} />;
      case "GridViewR":
        return (
          <GridViewResource
            ResourceData={data}
            setExcelGridRef={setExcelGridRef}
          />
        );
      case "GridViewJ":
        return (
          <GridViewJob ResourceData={data} setExcelGridRef={setExcelGridRef} />
        );
      default:
        return <ResourceView />;
    }
  };


  const [appliedFilters, setAppliedFilters] = React.useState<any>({
    stages: [],
    workStations: [],
    jobs: [],
    actionPreferences: [],
    timePreference: { startDate: null, endDate: null },
  });

  const [startDate, setStartDate] = useState<number | null>(null);
  const [endDate, setEndDate] = useState<number | null>(null);

  useEffect(() => {
    const allKeys = Object.keys(finalResult?.Resource_Data || {});
  
    let minStartDate: number | null = null;
    let maxEndDate: number | null = null;
  
    allKeys.forEach((key) => {
      const resource = finalResult.Resource_Data[key];
      resource.task_list.forEach((task: any) => {
        if (task.start_time) {
          if (minStartDate === null || task.start_time < minStartDate) {
            minStartDate = task.start_time;
          }
        }
        if (task.end_time) {
          if (maxEndDate === null || task.end_time > maxEndDate) {
            maxEndDate = task.end_time;
          }
        }
      });
    });
  
    // Convert epoch time to ISO date string (assuming epoch time is already in milliseconds)
    console.log("minStartDate", minStartDate)
    setStartDate(minStartDate ? minStartDate*1000: null);
    setEndDate(maxEndDate?  maxEndDate*1000: null);
  }, [finalResult]);
  useEffect(() => {
    // Here you can add logic to filter 'data' based on 'appliedFilters'
    const FilteredResourceData: any = _.cloneDeep(finalResult); // Start with the original data
    const { stages, workStations, jobs, actionPreferences, timePreference } =
      appliedFilters;
  
    // Helper function to check if a timestamp falls within the date range
    const isWithinDateRange = (timestamp: number) => {
      if (
        !timePreference ||
        (!timePreference.startDate && !timePreference.endDate)
      ) {
        return true; // No date filter applied
      }
  
      const taskDate = new Date(timestamp * 1000); // Convert Unix timestamp to Date
      const startDate = timePreference.startDate
        ? new Date(timePreference.startDate)
        : null;
      const endDate = timePreference.endDate
        ? new Date(timePreference.endDate)
        : null;
  
      // Set time to start/end of day for proper comparison
      if (startDate) {
        startDate.setHours(0, 0, 0, 0);
      }
      if (endDate) {
        endDate.setHours(23, 59, 59, 999);
      }
  
      // Check if task falls within the date range
      const afterStartDate = !startDate || taskDate >= startDate;
      const beforeEndDate = !endDate || taskDate <= endDate;
  
      return afterStartDate && beforeEndDate;
    };
  
    // Filter resources based on stages and workStations
    Object.keys(FilteredResourceData.Resource_Data).forEach((resourceId) => {
      const resource = FilteredResourceData.Resource_Data[resourceId];
  
      if (
        (stages.length > 0 && !stages.includes(resource.stage)) ||
        (workStations.length > 0 &&
          !workStations.includes(resource.work_station))
      ) {
        delete FilteredResourceData.Resource_Data[resourceId];
      } else {
        // If resource is kept, filter its task_list based on jobs, actionPreferences, and date range
        resource.task_list = resource.task_list.filter((task: any) => {
          // Job filter: Only apply if Job_id exists (not null/undefined)
          // If Job_id is null/undefined, it's not a job and should pass this filter
          const jobMatch = 
            !task.Job_id || // If no Job_id, always include (not a job)
            jobs.length === 0 || // If no job filter applied, include all
            jobs.includes(task.Job_id); // If Job_id exists, check if it's in the filter
  
          const actionPrefMatch =
            actionPreferences.length === 0 ||
            actionPreferences.includes(task.task_type);
  
          // Date range filtering - check if task overlaps with selected date range
          let dateMatch = true;
          if (
            timePreference &&
            (timePreference.startDate || timePreference.endDate)
          ) {
            // A task matches if either its start_time or end_time falls within the range,
            // or if the task spans across the entire selected range
            const taskStartWithinRange =
              task.start_time && isWithinDateRange(task.start_time);
            const taskEndWithinRange =
              task.end_time && isWithinDateRange(task.end_time);
  
            // Check if task spans across the selected date range
            const taskSpansRange =
              timePreference.startDate &&
              timePreference.endDate &&
              task.start_time &&
              task.end_time &&
              new Date(task.start_time * 1000) <=
                new Date(timePreference.startDate) &&
              new Date(task.end_time * 1000) >=
                new Date(timePreference.endDate);
  
            dateMatch =
              taskStartWithinRange || taskEndWithinRange || taskSpansRange;
          }
  
          return jobMatch && actionPrefMatch && dateMatch;
        });
      }
    });
  
    setData(FilteredResourceData);
  }, [appliedFilters]);

  const [isFilterModalOpen, setIsFilterModalOpen] = useState(false);

  return (
    <FinalResultSectionWrapper>
      <SchedulingActionToolbar
        onGoBack={() => {
          setStep("Upload");
        }}
        on
        currentView={currentView}
        setCurrentView={setCurrentView}
        setIsFilterModalOpen={setIsFilterModalOpen}
        appliedFilters={appliedFilters}
        setAppliedFilters={setAppliedFilters}
        gridRef={excelGridRef}
        startDate={startDate}
        endDate={endDate}
      />

      {getCurrentView()}
      {isFilterModalOpen && (
        <VFOverlayModal
          parentSelector="#main-content"
          openModal={isFilterModalOpen}
        >
          <FilterModal
            setIsFilterModalOpen={setIsFilterModalOpen}
            ResourceData={finalResult}
            appliedFilters={appliedFilters}
            setAppliedFilters={setAppliedFilters}
          />
        </VFOverlayModal>
      )}
    </FinalResultSectionWrapper>
  );
};

export default FinalResultSection;
