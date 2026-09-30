import React, { Suspense, lazy, useEffect, useState } from "react";
import { ChartWrapper, ResourceSectionWrapper, SkeletonBlock } from "./ResourceViewStyles";

const MyChart = lazy(() => import("./MyChart")); // still code-split

const GanttSkeleton = () => {
  return (
    <div>
      <SkeletonBlock height="30px" width="40%" />
      <SkeletonBlock height="30px" width="60%" />

      {[...Array(6)].map((_, i) => (
        <SkeletonBlock
          key={i}
          height="20px"
          width={`${50 + Math.random() * 40}%`}
        />
      ))}
    </div>
  );
};

const ResourceViewChart = ({ResourceData}:any) => {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setReady(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const data: any = ResourceData.Resource_Data;


  const allResources: { id: string; stage: string, work_station: string }[] = [];


  const allResourceIds= Object.keys(data);
  allResourceIds.forEach((key:string, index)=>{
    const val = {id: key, stage: data[key]?.stage, work_station: data[key]?.work_station};
    allResources.push(val);
  });

  const ColDef = [
    { title: "Stage", key: "stage", width: 150 },
    { title: "Work Station", key: "work_station", width: 150 },
  ];


  const RowData = allResources;

  const TaskData: {jobId: any, task_type: string, work_station: string, start: EpochTimeStamp, end:EpochTimeStamp }[] = [];

  allResourceIds.forEach((resId:string)=>{
    const tasks = data[resId]?.task_list || [];
    const work_st = data[resId]?.work_station || "";
    tasks.forEach((task:any)=>{
      const taskEntry = {
        jobId: task.Job_id || null,
        task_type: task.task_type,
        work_station: work_st,
        start: task.start_time,
        end: task.end_time,
      };
      TaskData.push(taskEntry);
    });
  });


  const colors = ResourceData.Task_master;
  



  return (
    <ResourceSectionWrapper>
      <ChartWrapper>
        {
        ready ? (
          <Suspense fallback={<GanttSkeleton />}>
            <MyChart RowData={RowData} ColDef={ColDef} TaskData={TaskData} primary_key={"work_station"} colors={colors} 
             Slot={ResourceData?.Slot }
            Attributes={ResourceData?.Attribute_Master || {}}
            />
          </Suspense>
        ) : (
        <GanttSkeleton />
        )}
      </ChartWrapper>
    </ResourceSectionWrapper>
  );
};

export default ResourceViewChart;
