import React from "react";
import { useUserData } from "../../../../../../context";
import VFButtonOutline from "../../../../../../components/VectorFLOW/commons/VFButtonOutline";
import VFButton from "../../../../../../components/VectorFLOW/commons/VFButton";
import { Checkbox, CloseButton, DateLabel, DateRow, DateWrapper, FilterBottomLeft, FilterBottomRight, FilterBottomSection, FilterContent, FilterHeaderTitle, FilterHeaderWrapper, FilterList, FilterSearchBar, FilterTab, FilterTabHeader, FilterTabLayout, FilterWrapper } from "./FilterModalStyles";

const FilterModal = ({ setIsFilterModalOpen, ResourceData, setAppliedFilters, appliedFilters }: any) => {
  const allJobs: any = [];
  const AllResourceIds = Object.keys(ResourceData.Resource_Data);
  AllResourceIds.forEach((resource: any) => {
    ResourceData.Resource_Data[resource].task_list.forEach((job: any) => {
      if (job.Job_id && !allJobs.includes(job.Job_id)) {
        allJobs.push(job.Job_id);
      }
    });
  });

  const allStages: any = [];
  AllResourceIds.forEach((resource: any) => {
    if (
      ResourceData.Resource_Data[resource].stage &&
      !allStages.includes(ResourceData.Resource_Data[resource].stage)
    ) {
      allStages.push(ResourceData.Resource_Data[resource].stage);
    }
  });

  const allWorkStations: any = [];
  AllResourceIds.forEach((resource: any) => {
    if (
      ResourceData.Resource_Data[resource].work_station &&
      !allWorkStations.includes(
        ResourceData.Resource_Data[resource].work_station
      )
    ) {
      allWorkStations.push(ResourceData.Resource_Data[resource].work_station);
    }
  });

  const allActionPreferences: any = Object.keys(ResourceData.Task_master);

  // Calculate min and max dates from Resource_Data
  const calculateDateRange = () => {
    let minTimestamp = Infinity;
    let maxTimestamp = -Infinity;

    AllResourceIds.forEach((resource: any) => {
      ResourceData.Resource_Data[resource].task_list.forEach((task: any) => {
        if (task.start_time) {
          minTimestamp = Math.min(minTimestamp, task.start_time);
        }
        if (task.end_time) {
          maxTimestamp = Math.max(maxTimestamp, task.end_time);
        }
      });
    });

    // Convert timestamps to Date objects (assuming they are in seconds, multiply by 1000 for milliseconds)
    const minDate = minTimestamp !== Infinity ? new Date(minTimestamp * 1000) : new Date();
    const maxDate = maxTimestamp !== -Infinity ? new Date(maxTimestamp * 1000) : new Date();

    return { minDate, maxDate };
  };

  const { minDate, maxDate } = calculateDateRange();

  const themeUi = useUserData().user.user.theme_ui;

  const [selectedFilters, setSelectedFilters] = React.useState<any>({
    ...appliedFilters,
    timePreference: appliedFilters.timePreference || { startDate: null, endDate: null }
  });
  
  // Search states for each tab
  const [searchTerms, setSearchTerms] = React.useState({
    stages: "",
    workStations: "",
    jobs: "",
    actionPreferences: ""
  });

  // Helper function to format date for input[type="date"]
  const formatDateForInput = (date: Date | string | null) => {
    if (!date) return '';
    const dateObj = date instanceof Date ? date : new Date(date);
    return dateObj.toISOString().split('T')[0];
  };

  // Calculate dynamic min/max for start and end dates
  const getStartDateConstraints = () => {
    const min = formatDateForInput(minDate);
    // Start date max should be either maxDate or selected endDate (whichever is earlier)
    const endDateSelected = selectedFilters.timePreference.endDate;
    let max = formatDateForInput(maxDate);
    
    if (endDateSelected) {
      const endDateFormatted = formatDateForInput(endDateSelected);
      max = endDateFormatted < max ? endDateFormatted : max;
    }
    
    return { min, max };
  };

  const getEndDateConstraints = () => {
    // End date min should be either minDate or selected startDate (whichever is later)
    const startDateSelected = selectedFilters.timePreference.startDate;
    let min = formatDateForInput(minDate);
    
    if (startDateSelected) {
      const startDateFormatted = formatDateForInput(startDateSelected);
      min = startDateFormatted > min ? startDateFormatted : min;
    }
    
    const max = formatDateForInput(maxDate);
    return { min, max };
  };

  const onSelectValue = (key: string, value: string) => {
    setSelectedFilters((prev: any) => {
      return prev[key].includes(value)
        ? {
            ...prev,
            [key]: prev[key].filter((s: any) => s !== value),
          }
        : {
            ...prev,
            [key]: [...prev[key], value],
          };
    });
  };

  const updateSearchTerm = (tabKey: string, value: string) => {
    setSearchTerms(prev => ({
      ...prev,
      [tabKey]: value
    }));
  };

  // Filter functions for each list
  const filterStages = () => {
    return allStages.filter((stage: string) => 
      stage.toLowerCase().includes(searchTerms.stages.toLowerCase())
    );
  };

  const filterWorkStations = () => {
    return allWorkStations.filter((ws: string) => 
      ws.toLowerCase().includes(searchTerms.workStations.toLowerCase())
    );
  };

  const filterJobs = () => {
    return allJobs.filter((job: string) => 
      job.toLowerCase().includes(searchTerms.jobs.toLowerCase())
    );
  };

  const filterActionPreferences = () => {
    return allActionPreferences.filter((pref: string) => 
      pref.toLowerCase().includes(searchTerms.actionPreferences.toLowerCase())
    );
  };

  const handleDateChange = (dateType: 'startDate' | 'endDate', date: Date | null) => {
    setSelectedFilters((prev: any) => ({
      ...prev,
      timePreference: {
        ...prev.timePreference,
        [dateType]: date
      }
    }));
  };

  const startDateConstraints = getStartDateConstraints();
  const endDateConstraints = getEndDateConstraints();

  return (
    <FilterWrapper>
      <FilterHeaderWrapper>
        <FilterHeaderTitle>
          <img
            src="/assets/img/scheduling/filter-icon.svg"
            alt="Filter"
            style={{ width: "16px", height: "16px", marginRight: "8px" }}
          />
          Select Filter
        </FilterHeaderTitle>
        <CloseButton onClick={() => setIsFilterModalOpen(false)}>×</CloseButton>
      </FilterHeaderWrapper>
  
      <FilterContent>
        <FilterTabLayout>
          {/* Stage */}
          <FilterTab>
            <FilterTabHeader>Stage</FilterTabHeader>
            <FilterSearchBar 
              type="text" 
              placeholder="Search Stage..."
              value={searchTerms.stages}
              onChange={(e) => updateSearchTerm("stages", e.target.value)}
            />
            <FilterList>
              {filterStages().map((stage: any, index: number) => {
                const id = `stage-${index}`;
                return (
                  <div
                    key={id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      padding: "4px 0",
                      gap: "6px",
                    }}
                    onClick={() => onSelectValue("stages", stage)}
                  >
                    <Checkbox
                      id={id}
                      theme={themeUi}
                      style={{ zoom: "0.5" }}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => onSelectValue("stages", stage)}
                      checked={selectedFilters.stages.includes(stage)}
                    />
                    <p>{stage}</p>
                  </div>
                );
              })}
            </FilterList>
          </FilterTab>
  
          {/* WorkStation */}
          <FilterTab>
            <FilterTabHeader>WorkStation</FilterTabHeader>
            <FilterSearchBar 
              type="text" 
              placeholder="Search WorkStation..." 
              value={searchTerms.workStations}
              onChange={(e) => updateSearchTerm("workStations", e.target.value)}
            />
            <FilterList>
              {filterWorkStations().map((ws: any, index: number) => {
                const id = `workstation-${index}`;
                return (
                  <div
                    key={id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      padding: "4px 0",
                      gap: "6px",
                    }}
                    onClick={() => onSelectValue("workStations", ws)}
                  >
                    <Checkbox
                      id={id}
                      style={{ zoom: 0.5 }}
                      theme={themeUi}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => onSelectValue("workStations", ws)}
                      checked={selectedFilters.workStations.includes(ws)}
                    />
                    <p>{ws}</p>
                  </div>
                );
              })}
            </FilterList>
          </FilterTab>
  
          {/* Job List */}
          <FilterTab>
            <FilterTabHeader>Job List</FilterTabHeader>
            <FilterSearchBar 
              type="text" 
              placeholder="Search Job..." 
              value={searchTerms.jobs}
              onChange={(e) => updateSearchTerm("jobs", e.target.value)}
            />
            <FilterList>
              {filterJobs().map((job: any, index: number) => {
                const id = `job-${index}`;
                return (
                  <div
                    key={id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      padding: "4px 0",
                      gap: "6px",
                    }}
                    onClick={() => onSelectValue("jobs", job)}
                  >
                    <Checkbox
                      id={id}
                      style={{ zoom: 0.5 }}
                      theme={themeUi}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => onSelectValue("jobs", job)}
                      checked={selectedFilters.jobs.includes(job)}
                    />
                    <p>{job}</p>
                  </div>
                );
              })}
            </FilterList>
          </FilterTab>

          {/* Time Preference */}
          <FilterTab>
            <FilterTabHeader>Time Preference</FilterTabHeader>
            <DateRow>
              <DateWrapper>
                <DateLabel htmlFor="start-date">Start Date</DateLabel>
                <input
                  style={{width: '90px', fontSize: '1rem', borderRadius: '4px', border: '1px solid #cecece', padding: '4px'}}
                  type="date"
                  id="start-date"
                  min={startDateConstraints.min}
                  max={startDateConstraints.max}
                  value={formatDateForInput(selectedFilters.timePreference.startDate)}
                  onChange={(e) => handleDateChange('startDate', e.target.value ? new Date(e.target.value) : null)}
                />
              </DateWrapper>
              <DateWrapper>
                <DateLabel htmlFor="end-date">End Date</DateLabel>
                <input
                  style={{width: '90px', fontSize: '1rem', borderRadius: '4px', border: '1px solid #cecece', padding: '4px'}}
                  type="date"
                  id="end-date"
                  min={endDateConstraints.min}
                  max={endDateConstraints.max}
                  value={formatDateForInput(selectedFilters.timePreference.endDate)}
                  onChange={(e) => handleDateChange('endDate', e.target.value ? new Date(e.target.value) : null)}
                />
              </DateWrapper>
            </DateRow>
          </FilterTab>
      
  
          {/* Action Preference */}
          <FilterTab>
            <FilterTabHeader>Action Preference</FilterTabHeader>
            <FilterSearchBar 
              type="text" 
              placeholder="Search Action Preference..."
              value={searchTerms.actionPreferences}
              onChange={(e) => updateSearchTerm("actionPreferences", e.target.value)}
            />
            <FilterList>
              {filterActionPreferences().map((pref: any, index: number) => {
                const id = `actionPref-${index}`;
                return (
                  <div
                    key={id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      padding: "4px 0",
                      gap: "6px",
                    }}
                    onClick={() => onSelectValue("actionPreferences", pref)}
                  >
                    <Checkbox
                      id={id}
                      style={{ zoom: 0.5 }}
                      theme={themeUi}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => onSelectValue("actionPreferences", pref)}
                      checked={selectedFilters.actionPreferences.includes(pref)}
                    />
                    <p>{pref}</p>
                  </div>
                );
              })}
            </FilterList>
          </FilterTab>
        </FilterTabLayout>
      </FilterContent>
  
      <FilterBottomSection>
        <FilterBottomLeft>
          <VFButtonOutline
            style={{ fontSize: "1.1rem", height: "3.2rem" }}
            themeUi={themeUi}
            onClick={() => {
              setSelectedFilters({
                stages: [],
                workStations: [],
                jobs: [],
                actionPreferences: [],
                timePreference: { startDate: null, endDate: null }
              });
              setSearchTerms({
                stages: "",
                workStations: "",
                jobs: "",
                actionPreferences: ""
              });
            }}
          >
            Reset Filter
          </VFButtonOutline>
        </FilterBottomLeft>
        <FilterBottomRight>
          <VFButtonOutline
            style={{ fontSize: "1.1rem", height: "3.2rem" }}
            themeUi={themeUi}
            onClick={() => setIsFilterModalOpen(false)}
          >
            Go Back!
          </VFButtonOutline>
          <VFButton
            style={{ fontSize: "1.1rem", height: "3.2rem" }}
            themeUi={themeUi}
            onClick={() => {
              setAppliedFilters(selectedFilters);
              setIsFilterModalOpen(false);
            }}
          >
            Apply Filter
          </VFButton>
        </FilterBottomRight>
      </FilterBottomSection>
    </FilterWrapper>
  );
};

export default FilterModal;