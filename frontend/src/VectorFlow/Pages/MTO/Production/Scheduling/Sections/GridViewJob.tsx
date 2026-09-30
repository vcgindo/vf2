import React, { useState, useEffect, useRef } from 'react'
import VFTable from '../../../Common/VFTable'
import { GridWrapper } from '../SchedulingStyles';
import { format } from 'date-fns';

// Custom cell renderer for multiple instances
const MultiInstanceCellRenderer = (props: any) => {
  const { value } = props;
  
  if (!value || !Array.isArray(value) || value.length === 0) {
    return <span>-</span>;
  }
  
  if (value.length === 1) {
    return <span>{value[0]}</span>;
  }
  
  // Multiple instances - show expandable view
  return (
    <div style={{ position: 'relative' }}>
      <div 
        style={{ 
          cursor: 'pointer', 
          color: 'rgb(130, 15, 76)',
          fontWeight: 500,
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}
      >
        <span>{value[0]}</span>
        <span style={{ 
          background: 'rgb(130, 15, 76)', 
          color: 'white', 
          borderRadius: '10px',
          padding: '2px 6px',
          fontSize: '0.75rem',
          fontWeight: 'bold'
        }}>
          +{value.length - 1}
        </span>
      </div>
    </div>
  );
};

// Tooltip renderer to show all instances
const MultiInstanceTooltip = (props: any) => {
  const { value } = props;
  
  if (!value || !Array.isArray(value)) return null;
  
  return (
    <div style={{ 
      padding: '8px',
      maxHeight: '300px',
      overflowY: 'auto',
      background: 'white',
      border: '1px solid #ccc',
      borderRadius: '4px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#333' }}>
        All Instances ({value.length})
      </div>
      {value.map((item: string, idx: number) => (
        <div 
          key={idx}
          style={{ 
            padding: '4px 8px',
            marginBottom: '4px',
            background: idx % 2 === 0 ? '#f5f5f5' : 'white',
            borderRadius: '3px',
            fontSize: '0.9rem'
          }}
        >
          <strong>Instance {idx + 1}:</strong> {item}
        </div>
      ))}
    </div>
  );
};

// Custom filter value getter for array fields
const arrayFilterValueGetter = (params: any) => {
  const value = params.data[params.colDef.field];
  if (!value || !Array.isArray(value) || value.length === 0) return '';
  // Return all values joined for filtering
  return value.join(' | ');
};

const GridViewJob = ({ResourceData, setExcelGridRef}: any) => {
  const [columnDefs, setColumnDefs] = useState<any>([]);
  const [rowData, setRowData] = useState<any>([]);

  const gridRef = useRef<any>(null)

  useEffect(() => {
    if (!ResourceData?.Resource_Data) return;

    // Extract unique stages
    const stageWorkStationMap = new Map<string, Set<string>>();
    
    Object.values(ResourceData.Resource_Data).forEach((resource: any) => {
      const stage = resource.stage;
      const workStation = resource.work_station;
      
      if (!stageWorkStationMap.has(stage)) {
        stageWorkStationMap.set(stage, new Set());
      }
      stageWorkStationMap.get(stage)?.add(workStation);
    });

    // Build dynamic column definitions
    const dynamicColumns: any[] = [
      {
        headerName: "Job List",
        field: "jobId",
        width: 120,
        pinned: 'left',
        filter: 'agMultiColumnFilter',
        filterParams: {
          buttons: ['reset', 'apply'],
          closeOnApply: true,
        }
      }
    ];

    // Create grouped columns for each stage
    Array.from(stageWorkStationMap.entries()).forEach(([stage, workStations]) => {
      const stageChildren: any[] = [];
      
      // Machine Name column with custom renderer and filter
      stageChildren.push({
        headerName: "Machine Name",
        field: `machine_name_${stage}`,
        width: 200,
        cellRenderer: MultiInstanceCellRenderer,
        tooltipField: `machine_name_${stage}`,
        tooltipComponent: MultiInstanceTooltip,
        tooltipComponentParams: { color: '#ececec' },
        filter: 'agTextColumnFilter',
        filterValueGetter: arrayFilterValueGetter
      });
      
      // Start Time column with custom renderer and filter
      stageChildren.push({
        headerName: "Start Time", 
        field: `start_${stage}`,
        width: 200,
        cellRenderer: MultiInstanceCellRenderer,
        tooltipField: `start_${stage}`,
        tooltipComponent: MultiInstanceTooltip,
        filter: 'agTextColumnFilter',
        filterValueGetter: arrayFilterValueGetter
      });
      
      // End Time column with custom renderer and filter
      stageChildren.push({
        headerName: "End Time",
        field: `end_${stage}`, 
        width: 200,
        cellRenderer: MultiInstanceCellRenderer,
        tooltipField: `end_${stage}`,
        tooltipComponent: MultiInstanceTooltip,
        filter: 'agTextColumnFilter',
        filterValueGetter: arrayFilterValueGetter
      });

      // Add the parent column with children
      dynamicColumns.push({
        headerName: stage,
        children: stageChildren
      });
    });

    setColumnDefs(dynamicColumns);
  }, [ResourceData]);

  useEffect(() => {
    if (!ResourceData?.Resource_Data) return;

    // Generate row data - store arrays for multiple instances
    const jobMap = new Map<string, any>();
    
    Object.entries(ResourceData.Resource_Data).forEach(([resourceId, resource]: [string, any]) => {
      const stage = resource.stage;
      const workStation = resource.work_station;
      
      resource.task_list?.forEach((task: any) => {
        if (task.Job_id) {
          const jobId = task.Job_id;
          
          if (!jobMap.has(jobId)) {
            jobMap.set(jobId, { 
              jobId,
              // Initialize arrays for each stage
              [`machine_name_${stage}`]: [],
              [`start_${stage}`]: [],
              [`end_${stage}`]: []
            });
          }
          
          const jobData = jobMap.get(jobId);
          
          // Initialize arrays if they don't exist for this stage
          if (!jobData[`machine_name_${stage}`]) {
            jobData[`machine_name_${stage}`] = [];
          }
          if (!jobData[`start_${stage}`]) {
            jobData[`start_${stage}`] = [];
          }
          if (!jobData[`end_${stage}`]) {
            jobData[`end_${stage}`] = [];
          }
          
          // Format time
          const formatTime = (timestamp: number) => {
            return format(new Date(timestamp * 1000), 'PPpp');
          };
          
          // Push to arrays (allowing multiple instances)
          jobData[`machine_name_${stage}`].push(workStation);
          jobData[`start_${stage}`].push(formatTime(task.start_time));
          jobData[`end_${stage}`].push(formatTime(task.end_time));
        }
      });
    });

    setRowData(Array.from(jobMap.values()));
  }, [ResourceData]);

  return (
    <GridWrapper>
      <VFTable
        key={"job-grid"}
        ref={gridRef}
        columnDefs={columnDefs}
        rowData={rowData}
        suppressRowClickSelection={true}
        defaultColDef={{
          sortable: true,
          filter: true,
          resizable: true,
          floatingFilter: true,
        }}
        tooltipShowDelay={0}
        tooltipHideDelay={2000}
        rowClass='my-row-class'
        getRowClass={params => {
          if (params && params.node && params.node.rowIndex && params?.node?.rowIndex % 2 === 0) {
            return 'my-shaded-effect';
          }
        }}
        onGridReady={()=>{
          setExcelGridRef(gridRef)
        }}
        animateRows={true}
        rowSelection="single"
        pagination={false}
        paginationPageSize={10}
      />
    </GridWrapper>
  )
}

export default GridViewJob