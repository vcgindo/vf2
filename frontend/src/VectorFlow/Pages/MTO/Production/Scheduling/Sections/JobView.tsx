import React, { Suspense, lazy, useEffect, useState } from "react";
import styled, { keyframes } from "styled-components";
import { TaskBar, TooltipRow, TooltipWrapper } from "../components/MyChartStyles";
import { format } from "date-fns";
import { ChartWrapper, SectionWrapper, SkeletonBlock } from "../SchedulingStyles";

const MyChart = lazy(() => import("../components/MyChart")); // still code-split



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

const JobView = ({ResourceData}: any) => {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setReady(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const data: any = ResourceData.Resource_Data;

  const allResources: { id: string; stage: string; work_station: string }[] =
    [];

  const allResourceIds = Object.keys(data);
  allResourceIds.forEach((key: string, index) => {
    const val = {
      id: key,
      stage: data[key]?.stage,
      work_station: data[key]?.work_station,
    };
    allResources.push(val);
  });

  const ColDef = [{ title: "Job List", key: "jobId", width: 150 }];

  const JobData: any = [];
  allResourceIds.forEach((re) => {
    const currentTask_list = data[re]?.task_list || [];
    const tempJobList: string[] = [];
    currentTask_list.forEach((t: any) => {
      if (t.Job_id && !tempJobList.includes(t.Job_id)) {
        JobData.push(t.Job_id);
      }
    });
  });

  const RowData = Array.from(new Set(JobData)).map((j: any) => ({ jobId: j }));

  const TaskData: {
    jobId: any;
    task_type: string;
    work_station: string;
    start: EpochTimeStamp;
    end: EpochTimeStamp;
  }[] = [];

  allResourceIds.forEach((resId: string) => {
    const tasks = data[resId]?.task_list || [];
    const work_st = data[resId]?.work_station || "";
    const stage = data[resId]?.stage || "";
    tasks.forEach((task: any) => {
      if (!task.Job_id) return; // Skip tasks without Job_id
      const taskEntry = {
        jobId: task.Job_id || null,
        task_type: task.task_type,
        work_station: work_st,
        stage: stage,
        start: task.start_time,
        end: task.end_time,
      };
      TaskData.push(taskEntry);
    });
  });


  const colors:any = ResourceData.Workstation_master;

  const CustomTaskBar = ({ taskIdx, left, width, task }:any) => {

    return (
      <TaskBar
        key={taskIdx}
        left={left}
        width={width}
        backgroundColor={colors?.[task.stage] ?? "#cecece"}
      >
        {task.stage + " : "+ task.work_station}
      </TaskBar>
    );
  };

  const CustomTooltip = (
      task: any,
      taskStartOffset: any,
      taskEndOffset: any,
      startDate: any,
      Attributes: any
    ) => {
      return (
        <TooltipWrapper>
          <TooltipRow>
            <div>
              <strong>{task.stage +" : "+ task.work_station}</strong>
            </div>
            <div style={{ color: "#cecece" }}>
              {task.jobId ? task.jobId : task.task_type}
            </div>
          </TooltipRow>
          {
                    task.jobId && Attributes && Attributes[task.jobId] &&
                    Object.keys(Attributes[task.jobId]).map((attrKey, idx)=>(
                      <TooltipRow key={idx}>
                         <div style={{ color: "#cecece" }}>
                          {attrKey}:
                        </div>
                        <div style={{ color: "#cecece" }}>
                        {Attributes[task.jobId][attrKey]}
                        </div>
                      </TooltipRow>
                    ))
                  }
          <div style={{ width: "100%", borderTop: "1px dashed #666666" }}></div>
          <TooltipRow>
            <div>
              <strong>Start:</strong>
            </div>
            <div>
              {format(new Date(startDate.getTime() + taskStartOffset), "PPpp")}
            </div>
          </TooltipRow>
  
          <TooltipRow>
            <div>
              <strong>End:</strong>
            </div>
            <div>
              {format(new Date(startDate.getTime() + taskEndOffset), "PPpp")}
            </div>
          </TooltipRow>
        </TooltipWrapper>
      );
    };

  return (
    <SectionWrapper>
      <ChartWrapper>
        {ready ? (
          <Suspense fallback={<GanttSkeleton />}>
            <MyChart
              RowData={RowData}
              ColDef={ColDef}
              TaskData={TaskData}
              primary_key="jobId"
              colors={colors}
              CustomTaskBar={CustomTaskBar}
              CustomTooltip={CustomTooltip}
              Slot={ResourceData?.Slot}
              Attributes={ResourceData?.Attribute_Master|| {}}
            />
          </Suspense>
        ) : (
          <GanttSkeleton />
        )}
      </ChartWrapper>
    </SectionWrapper>
  );
};

export default JobView;
