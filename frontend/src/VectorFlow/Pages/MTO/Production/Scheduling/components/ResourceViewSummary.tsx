import React, { useEffect, useRef, useState } from "react";
import VFTable from "../../../Common/VFTable";
import { AgGridReactProps } from "ag-grid-react";
// eslint-disable-next-line import/no-unresolved
import "../gridStyles.css";
import { FilterSection, GridWrapper, SectionWrapper, Tab, ToggleButton, ToggleWrapper, WorkStationDropDown } from "./ResourceViewStyles";




const ResourceViewSummary = ({ ResourceData, setExcelGridRef}: any) => {    

  const [active, setActive] = useState("Percentage Wise");
  const allWorkStations:any = new Set(Object.values(ResourceData.Resource_Data || {}).map((r: any) => r.work_station));

  const [activeWorkStation, setActiveWorkStation] = useState<any>("All Work Stations");

const options = ["Percentage Wise", "Day Wise", "Hrs Wise", "Count Wise"];

  const agGridProps: AgGridReactProps = {

      defaultColDef: {
          sortable: true,
          cellRenderer: (params:any) => {
            if(active === "Count Wise") return params?.value;
            if (params?.value == null) return "";
            if(isNaN(params?.value))return params?.value;
            if(!params?.value?.toFixed)return params?.value;
            const [intPart, decPart = ""] = String(params?.value?.toFixed(2)).split(".");
            return (
              <>
              <span style={{display: "inline-block", textAlign: "right", minWidth: '40px'}}>
                {intPart}
              </span>
              <span  style={{display: "inline-block", textAlign: "left", minWidth: '20px'}}>
                .{decPart}
              </span>
              </>
            );
          },
          cellStyle: { fontFamily: "monospace" },
          filter: 'agMultiColumnFilter',
          resizable: true,
          floatingFilter: true,
          flex: 1,
      },
      rowClass: 'my-row-class',
    
      // all even rows assigned 'my-shaded-effect'
      getRowClass: params => {
          if (params && params.node && params.node.rowIndex &&  params?.node?.rowIndex % 2 === 0) {
              return 'my-shaded-effect';
          }
      },
      suppressRowClickSelection: true,
      animateRows: true,
      rowSelection: "single",
      pagination: false,
      paginationPageSize: 10,

  }

  const [colDef, setColDef] = useState<any>([]);
  const [rowData, setRowData] = useState<any>([]);


  useEffect(()=>{
      const ColDef = [
          { headerName: 'Workstation', colId: 'work_station',filter: 'agMultiColumnFilter', field: 'work_station', width: 120, flex: 1, position: 1 },
      ];
  
      const TaskTypes = Object.keys(ResourceData.Task_master || {});
  
      TaskTypes.forEach((type: any, index: number) => {
          ColDef.push({ headerName: type,filter: 'agNumberColumnFilter', colId: type, field: type, width: 120, flex: 1, position: index + 2 });
      });

      if(active !== "Percentage Wise"){
        ColDef.push({headerName: "Total", colId: "total", field: "total",filter: 'agNumberColumnFilter', width: 120, flex: 1, position: TaskTypes.length + 2})
      }

      setColDef(ColDef);

  },[ResourceData.Task_master, active])

  // Unified function to generate data for all active modes
  const generateSummaryData = () => {
    const data: any = ResourceData.Resource_Data || {};
  
    const allResources: { id: string; stage: string; work_station: string }[] = [];
  
    const allResourceIds = Object.keys(data);
    allResourceIds.forEach((key: string) => {
      const val = {
        id: key,
        stage: data[key]?.stage,
        work_station: data[key]?.work_station,
      };
      allResources.push(val);
    });
  
    const workStationSet = new Set(allResources.map((r) => r.work_station));
    const filteredWorkStations =
      activeWorkStation === "All Work Stations" || !activeWorkStation
        ? Array.from(workStationSet) // Include all workstations
        : Array.from(workStationSet).filter((ws) => ws === activeWorkStation);

    const summaryData: any[] = [];
  
    filteredWorkStations.forEach((ws) => {
      const resourcesInWS = allResources.filter((r) => r.work_station === ws);
      const taskTypeCount: { [key: string]: number } = {};
      const taskTypeDuration: { [key: string]: number } = {};
      let totalCount = 0;
  
      let minStartDate = Infinity;
      let maxEndDate = -Infinity;
  
      resourcesInWS.forEach((res) => {
        const tasks = data[res.id]?.task_list || [];
        tasks.forEach((task: any) => {
          const type = task.task_type || "unknown";
          // Unix timestamps are already in seconds, convert to milliseconds
          const startTime = task.start_time * 1000;
          const endTime = task.end_time * 1000;
  
          // Update min and max dates for the workstation range
          minStartDate = Math.min(minStartDate, startTime);
          maxEndDate = Math.max(maxEndDate, endTime);
  
          // Calculate task duration in hours
          const taskDuration = (endTime - startTime) / (1000 * 60 * 60); // Convert milliseconds to hours
          taskTypeDuration[type] = (taskTypeDuration[type] || 0) + taskDuration;
  
          taskTypeCount[type] = (taskTypeCount[type] || 0) + 1;
          totalCount += 1;
        });
      });
  
      // Calculate total time span of the workstation (from earliest start to latest end)
      const totalTimeSpanHours = minStartDate !== Infinity && maxEndDate !== -Infinity 
        ? (maxEndDate - minStartDate) / (1000 * 60 * 60) // Convert milliseconds to hours
        : 0;
  
      const entry: any = { work_station: ws };
      
      Object.keys(ResourceData.Task_master || {}).forEach((type) => {
        const duration = taskTypeDuration[type] || 0;
        const count = taskTypeCount[type] || 0;

        if (active === "Percentage Wise") {
          entry[type] = totalTimeSpanHours > 0
            ? ((duration / totalTimeSpanHours) * 100)
            : 0;
        } else if (active === "Day Wise") {
          // Convert hours to days
          entry[type] = (duration / 24);
        } else if (active === "Hrs Wise") {
          // Show hours directly
          entry[type] = duration;
        } else if (active === "Count Wise") {
          // Show count of tasks
          entry[type] = count;
        }
      });
  
      // Add total column for non-percentage modes
      if (active !== "Percentage Wise") {
        if (active === "Count Wise") {
          entry["total"] = totalCount;
        } else if (active === "Day Wise") {
          const totalTaskDuration = Object.values(taskTypeDuration).reduce((sum: number, val: any) => sum + val, 0);
          entry["total"] = (totalTaskDuration / 24)?.toFixed(2) ;
        } else if (active === "Hrs Wise") {
          const totalTaskDuration = Object.values(taskTypeDuration).reduce((sum: number, val: any) => sum + val, 0);
          entry["total"] = totalTaskDuration?.toFixed(2);
        }
      }
  
      summaryData.push(entry);
    });
  
    return summaryData;
  };

  useEffect(() => {
    setRowData(generateSummaryData());
  }, [active, activeWorkStation, ResourceData]);


  const gridRef = useRef<any>(null);

return (
  <SectionWrapper>
      <Tab>Summary</Tab>
    <GridWrapper>
      {/* Content inside the grid */}

    <FilterSection>

      <WorkStationDropDown placeholder="Select Work Station" value={activeWorkStation ||"" } onChange={(e) => {setActiveWorkStation(e.target.value)}}>
        <option key={"All Work Stations"} value={"All Work Stations"}>
          {"All Work Stations"}
        </option>
       {
         Array.from(allWorkStations).map((ws:any) => (
          <option key={ws} value={ws}>
            {ws}
          </option>
        ))
       }
      </WorkStationDropDown>

      <ToggleWrapper>
    {options.map((opt) => (
      <ToggleButton
        key={opt}
        active={active === opt}
        onClick={() => setActive(opt)}
      >
        {opt}
      </ToggleButton>
    ))}
  </ToggleWrapper>
    </FilterSection>

      <VFTable ref={gridRef} {...agGridProps}  columnDefs={colDef} rowData={rowData} onGridReady={()=>{
        setExcelGridRef(gridRef)
      }} />

    </GridWrapper>
  </SectionWrapper>
);
};

export default ResourceViewSummary;
