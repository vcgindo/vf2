import React, { useState, useEffect, useRef } from 'react'
import VFTable from '../../../Common/VFTable'
import { GridWrapper } from '../SchedulingStyles';
import { format } from 'date-fns';



const GridViewResource = ({ResourceData, setExcelGridRef}: any) => {
  const [columns, setColumns] = useState<any>([]);
  const [rowData, setRowData] = useState<any>([]);

  const gridRef = useRef<any>(null)

  useEffect(() => {
    if (!ResourceData?.Resource_Data) {
      setColumns([]);
      return;
    }

    // Extract unique task types from all resources
    const taskTypes = new Set<string>();
    Object.values(ResourceData.Resource_Data).forEach((resource: any) => {
      resource.task_list?.forEach((task: any) => {
        if (task.task_type) {
          taskTypes.add(task.task_type);
        }
      });
    });


    // Define base column structure
    const columnDefs:any = [
      {
        headerName: "Stage",
        field: "stage",
        width: 120,
        pinned: 'left',
        filter: 'agSetColumnFilter'
      },
      {
        headerName: "Machine Name", 
        field: "machineName",
        width: 200,
        pinned: 'left',
        filter: 'agSetColumnFilter'
      },
      {
        headerName: "Min",
        children: [
          {
            headerName: "Start",
            field: "minStart",
            width: 150,
            filter: 'agTextColumnFilter'
          },
          {
            headerName: "End", 
            field: "minEnd",
            width: 150,
            filter: 'agTextColumnFilter'
          }
        ]
      },
      {
        headerName: "Max",
        children: [
          {
            headerName: "Start",
            field: "maxStart", 
            width: 150,
            filter: 'agTextColumnFilter'
          },
          {
            headerName: "End",
            field: "maxEnd",
            width: 150,
            filter: 'agTextColumnFilter'
          }
        ]
      },
      {
        headerName: "Elapsed Time",
        field: "elapsedTime",
        width: 120,
        filter: 'agNumberColumnFilter'
      }
    ];

    const Task_types = Object.keys(ResourceData?.Task_master || {});
    Task_types.forEach((taskType) => {
      columnDefs.push(
        {
          headerName: taskType,
          children: [
            {
              headerName: "Count",
              field: taskType + "_count",
              width: 120,
              filter: 'agNumberColumnFilter'
            },
            {
              headerName: "Hrs", 
              field: taskType + "_hrs",
              width: 120,
              filter: 'agNumberColumnFilter'
            }
          ]
        },
      )
    });

    setColumns(columnDefs);
  }, [ResourceData]);

  useEffect(() => {
    if (!ResourceData?.Resource_Data) return;

    // Process resource data to generate row data
    const resourceRows: any[] = [];
    
    // Extract unique task types for consistent field naming
    const taskTypes = new Set<string>();
    Object.values(ResourceData.Resource_Data).forEach((resource: any) => {
      resource.task_list?.forEach((task: any) => {
        if (task.task_type) {
          taskTypes.add(task.task_type);
        }
      });
    });
    
    Object.entries(ResourceData.Resource_Data).forEach(([resourceId, resource]: [string, any]) => {
      const stage = resource.stage;
      const machineName = resource.work_station;
      const taskList = resource.task_list || [];
      
      if (taskList.length === 0) return;

      // Find min and max times for this resource
      let minStartTime = Infinity;
      let minEndTime = Infinity;
      let maxStartTime = -Infinity;
      let maxEndTime = -Infinity;
      let totalTaskDuration = 0;
      
      // Initialize task type counters
      const taskTypeData: { [key: string]: { count: number; hours: number } } = {};
      Array.from(taskTypes).forEach(type => {
        taskTypeData[type] = { count: 0, hours: 0 };
      });

      taskList.forEach((task: any) => {
        const startTime = task.start_time;
        const endTime = task.end_time;
        const taskType = task.task_type;
        
        // Update min and max times only for "job" task types
        if (taskType === "JOB") {
          // Update min times (earliest job task)
          if (startTime < minStartTime) {
            minStartTime = startTime;
            minEndTime = endTime;
          }
          
          // Update max times (latest job task)  
          if (endTime > maxEndTime) {
            maxEndTime = endTime;
            maxStartTime = startTime;
          }
        }
        
        // Calculate task duration and add to total (for all tasks)
        const taskDuration = (endTime - startTime) / 3600; // Convert seconds to hours
        totalTaskDuration += taskDuration;
        
        // Update task type counters (for all tasks)
        if (taskType && taskTypeData[taskType]) {
          taskTypeData[taskType].count += 1;
          taskTypeData[taskType].hours += taskDuration;
        }
      });

      // Format time function
      const formatTime = (timestamp: number) => {
        return format(new Date(timestamp * 1000), 'PPpp');
      };

      // Create base row data
      const rowData: any = {
        stage,
        machineName,
        minStart: minStartTime !== Infinity ? formatTime(minStartTime) : '-',
        minEnd: minEndTime !== Infinity ? formatTime(minEndTime) : '-',
        maxStart: maxStartTime !== -Infinity ? formatTime(maxStartTime) : '-', 
        maxEnd: maxEndTime !== -Infinity ? formatTime(maxEndTime) : '-',
        elapsedTime: Math.round(totalTaskDuration) // Round to nearest hour
      };
      
      // Add task type data to row
      Array.from(taskTypes).forEach(taskType => {
        rowData[`${taskType}_count`] = taskTypeData[taskType].count;
        rowData[`${taskType}_hrs`] = Math.round(taskTypeData[taskType].hours * 10) / 10; // Round to 1 decimal place
      });

      resourceRows.push(rowData);
    });

    // Sort by stage and then by machine name
    resourceRows.sort((a, b) => {
      if (a.stage !== b.stage) {
        return a.stage.localeCompare(b.stage);
      }
      return a.machineName.localeCompare(b.machineName);
    });

    setRowData(resourceRows);
  }, [ResourceData]);

  return (
    <GridWrapper>
      <VFTable
        key={"resource-grid"}
        ref={gridRef}
        columnDefs={columns}
        rowData={rowData}
        defaultColDef={{
          sortable: true,
          filter: true,
          resizable: true,
          floatingFilter: true,
        }}
        
        rowClass='my-row-class'
        getRowClass={params => {
          if (params && params.node && params.node.rowIndex && params?.node?.rowIndex % 2 === 0) {
            return 'my-shaded-effect';
          }
        }}
        onGridReady={()=>{
          setExcelGridRef(gridRef)
        }}
        suppressRowClickSelection={true}
        animateRows={true}
        rowSelection="single"
      />
    </GridWrapper>
  )
}

export default GridViewResource