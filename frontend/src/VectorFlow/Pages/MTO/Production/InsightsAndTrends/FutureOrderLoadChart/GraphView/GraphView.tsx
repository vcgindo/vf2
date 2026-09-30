import { useEffect, useMemo, useRef, useState } from "react";
import { ChartWrapper, GraphViewWrapper } from "../../../../../../../VectorFlow/Pages/MTO/Procurement/InsightsAndTrends/RMPMOrderwiseCoverage/GraphView/styles";
import { SCChartContainer, SCHorizontalDivider } from "../../STPLAndFullKits/styles";
import { AgCharts } from "ag-charts-react";
import { ApplyZoomOut } from "../../../OrderRescheduling/styles";
import VFFloatingTab from "../../../../../../../components/VectorFLOW/commons/VFFloatingTab";
import { MyFutureOrderTabsFix } from "../styles";
import CustomLegend from "../../../../../../../VectorFlow/Pages/MTO/Common/CustomLegend/index";

const GraphView = ({ Viewtabs, currView, setCurrView, selectedCCR, horizonData, graphData, cwl, selectedAction, currTab }: any) => {
  
  const [cwlValue, setCwlValue] = useState(0);
  const [selectedCCRHorizonDate, setSelectedCCRHorizonDate] = useState<any>('');
  const [horizonDateRange, setHorizonDateRange] = useState<{startDate: string, endDate: string} | null>(null);

  useEffect(() => {
    if (selectedCCR?.value && horizonData && horizonData.length > 0) {
      const ccrHorizonItem = horizonData.find((item: any) => item.ccr === selectedCCR.value);
      const horizonDate = ccrHorizonItem?.horizon_date || null;
      
      setSelectedCCRHorizonDate(horizonDate);
      
      if (horizonDate) {
        const today = new Date();
        const todayString = today.toISOString().split('T')[0];    
        setHorizonDateRange({
          startDate: todayString,
          endDate: horizonDate
        });
        
      } else {
        setHorizonDateRange(null);
      }
    } else {
      setSelectedCCRHorizonDate(null);
      setHorizonDateRange(null);
    }
  }, [selectedCCR, horizonData]);

  useEffect(() => {
    if (graphData?.data && cwl) {
      const a = graphData?.data?.map((item: any) => item.ccr);
      const b = cwl.map((item: any) => item.value);
      const matchedCCR = a.find((ccr: any) => b.includes(ccr));
      const matchedCWL = matchedCCR ? cwl.find((item: any) => item.value === matchedCCR)?.cumulative_wip_limit: 0;
          setCwlValue(matchedCWL);
    }
  }, [selectedCCR, cwl]);

  // Helper function to check if a date falls within the horizon range
  const isDateInHorizonRange = (dateToCheck: string) => {
    if (!horizonDateRange) return false;

    const checkDate = new Date(dateToCheck);
    const startDate = new Date(horizonDateRange.startDate);
    const endDate = new Date(horizonDateRange.endDate);

    if (currView === 'weekly') {
    // ["31st Aug", "6th Sep"]
      const dateParts = dateToCheck.split(' - ');
      if (dateParts.length === 2) {
        const weekEndStr = dateParts[1].trim();

    // Extract day and month 
      const weekEndMatch = weekEndStr.match(/(\d+)(?:st|nd|rd|th)?\s+([A-Za-z]+)/);

        if (weekEndMatch) {
          const day = weekEndMatch[1]; //6
          const month = weekEndMatch[2]; //sep
          
          const startYear = new Date(horizonDateRange.startDate).getFullYear(); //2025
          
    // Parse start date of the week
          const weekStartStr = dateParts[0].trim();
          const weekStartMatch = weekStartStr.match(/(\d+)(?:st|nd|rd|th)?\s+([A-Za-z]+)/);
          if (weekStartMatch) {
            const startDay = weekStartMatch[1]; //31
            const startMonth = weekStartMatch[2]; //aug
            
            let weekStartDate = new Date(`${startMonth} ${startDay} ${startYear}`);
            let weekEndDate = new Date(`${month} ${day} ${startYear}`);
            //Dec 2025 - Jan 2026
            if (weekEndDate < weekStartDate) {
              weekEndDate = new Date(`${month} ${day} ${startYear + 1}`);
            }
            
            if (weekStartDate.getFullYear() === startYear && weekStartDate < startDate) {
              weekStartDate = new Date(`${startMonth} ${startDay} ${startYear + 1}`);
              weekEndDate = new Date(`${month} ${day} ${startYear + 1}`);
            }
            
            const weekOverlapsHorizon = weekStartDate <= endDate && weekEndDate >= startDate;
            
            return weekOverlapsHorizon;
          }
        }
      }
      return false;
    }

    if (currView === 'monthly') {
      // "Sep 25"
      const monthMatch = dateToCheck.match(/([A-Za-z]+)\s+(\d{2,4})/);
      if (monthMatch) {
        const month = monthMatch[1]; //sep
        let year = parseInt(monthMatch[2]); //25
        
        if (year < 100) {
          year = 2000 + year; // 25 to 2025 convert
        }
        const monthStartDate = new Date(`${month} 1, ${year}`);
        const monthEndDate = new Date(year, monthStartDate.getMonth() + 1, 0);
        
        monthStartDate.setHours(0, 0, 0, 0);
        monthEndDate.setHours(23, 59, 59, 999);
        
        const todayNormalized = new Date(startDate);
        todayNormalized.setHours(0, 0, 0, 0);
        
        const horizonNormalized = new Date(endDate);
        horizonNormalized.setHours(23, 59, 59, 999);
        const monthOverlapsHorizon = monthStartDate <= horizonNormalized && monthEndDate >= todayNormalized;
        
        return monthOverlapsHorizon;
      }
      return false;
    }
    
    return checkDate >= startDate && checkDate <= endDate;
  };

  const transformedData = useMemo(() => {
    if (!graphData?.data) return [];
      return graphData.data.map((item: any, index: number) => {
      const isInHorizonRange = isDateInHorizonRange(item.date);
      const tag = item.tag;
  
      if (currView === "daily") {
        return {
          date: item.date,
          load: tag !== "Past Scheduling" ? item.load : "",
          holiday: item.is_holiday,
          past: tag === "Past Scheduling" ? item.load : "",
          limit: cwlValue,
          type: item.is_holiday ? "holiday" : "load",
          horizonDate: selectedCCRHorizonDate,
          isInHorizonRange,
        };
      }
  
        if (currView === "weekly" || currView === "monthly") {
        return {
          date: item.date,
          load: index===0? ( item.load - graphData.pastorder_load ): item.load, //item.load, 
          holiday: item.is_holiday,
          past: index === 0 ? graphData.pastorder_load : "", 
          limit: cwlValue,
          type: item.is_holiday ? "holiday" : "load",
          horizonDate: selectedCCRHorizonDate,
          isInHorizonRange,
        };
      }
    });
  }, [graphData, currView, cwlValue, selectedCCRHorizonDate, horizonDateRange]);
  
  // Helper function to get tooltip renderer with current currTab value
  const getLoadTooltipRenderer = () => ({
    renderer: ({ datum }: any) => {
      const label = currTab === "Load Wise" ? "Load" : "Pending CCR Quantity";
      return `
        <div style="
          background: white;
          color: #000;
          padding: 12px 16px;
          min-width: 120px;
          text-align: center;
          border-radius: 6px;
          box-shadow: 0 0 6px rgba(0,0,0,0.15);
        ">
          <div style="color:#555; font-weight:600; font-size:12px; margin-bottom:4px;">
            ${label}
          </div>
          <div style="font-size:12px;">${datum.load}</div>
        </div>
      `;
    }
  });

  const [chartoptions, setChartOptions] = useState<any>({
    series: [
      {
        type: 'bar',
        xKey: 'date',
        yKey: 'load',
        yName:'Future Order',
        stacked: true,
        visible: true,
        fill: '#F4BD8E',
        stroke: '#F4BD8E',
        legendItemName: 'Load',
        tooltip: getLoadTooltipRenderer(),
        itemStyler: ({ datum }: any) => {
          if (datum.type === 'holiday') {
            return { fillOpacity: 0, strokeOpacity: 0 };
          }
          return {
            fill: '#F4BD8E',
            stroke: '#F4BD8E',
          };
        },
      },
      {
        type: 'bar',
        xKey: 'date',
        yKey: 'load',
        yName:'Holiday',
        stacked: true,
        visible: true,
        fill: '#999999',
        stroke: '#999999',
        legendItemName: 'Holiday',
        name:'holiday',
        tooltip: getLoadTooltipRenderer(),
        itemStyler: ({ datum }: any) => {
          if (datum.type === 'holiday') {
            return {
              fill: '#999999',
              stroke: '#999999',
            };
          }
          return { fillOpacity: 0, strokeOpacity: 0 };
        },
      },
      {
        type: 'bar',
        xKey: 'date',
        yKey: 'past',
        yName:'Past',
        stacked: true,
        visible: true,
        stroke: '#FF5959',
        fill: '#FF5959',
        strokeWidth: 2,
        legendItemName: 'Past',
        label: {
          enabled: false  
        },
        tooltip: {
          renderer: ({ datum }: any) => `
            <div style="
              background: white;
              color: #000;
              padding: 12px 16px;
              min-width: 100px;
              text-align: center;
              border-radius: 6px;
              box-shadow: 0 0 6px rgba(0,0,0,0.15);
            ">
              <div style="color:#FF5959; font-weight:600; font-size:12px; margin-bottom:4px;">
                Past
              </div>
              <div style="font-size:12px;">${datum.past}</div>
            </div>
          `
        },
        itemStyler: ({ datum }: any) =>
          datum.past ? {} : { fillOpacity: 0, strokeOpacity: 0 }
      },
      {
        type: 'line',
        xKey: 'date',
        yKey: 'limit',
        yName:'Limit',
        stroke: '#820f4c',
        strokeWidth: 2,
        strokeDashArray: [5, 5],
        visible: true,
        legendItemName: 'Limit',
        marker: {
          enabled: false
        },
        label: {
          enabled: false  
        },
        tooltip: {
          renderer: ({ datum }: any) => `
            <div style="
              background: white;
              color: #000;
              padding: 12px 16px;
              min-width: 120px;
              text-align: center;
              border-radius: 6px;
              box-shadow: 0 0 6px rgba(0,0,0,0.15);
            ">
              <div style="color:#820f4c; font-weight:600; font-size:12px; margin-bottom:4px;">
                Limit
              </div>
              <div style="font-size:12px;">${datum.limit}</div>
            </div>
          `
        }
      }
    ],
    axes: [
      {
        type: 'category',
        position: 'bottom',
        title: { text: 'Timeline For Upcoming Orders', fontSize: 12, fontWeight: 300 },
        label: { fontSize: 10, fontWeight: 300, color: '#111' }
      },
      {
        type: 'number',
        position: 'left',
        title: {
          text: 'Load in Days',
          fontSize: 12, 
          fontWeight: 300
        },
        label: { fontSize: 10, fontWeight: 300, color: '#111' }
      }
    ],
    height: 370,
    legend: {
      enabled: false,
    }
  });

  // CONSOLIDATED: Update tooltips, axes, and crossLines when currTab or cwlValue changes
  useEffect(() => {
    setChartOptions((prevOptions: any) => {
      const limitSeries = prevOptions.series.find((s: any) => s.legendItemName === 'Limit');
      const isLimitVisible = limitSeries ? limitSeries.visible : true;
      
      return {
        ...prevOptions,
        series: prevOptions.series.map((series: any) => {
          if (series.yKey === 'load') {
            return {
              ...series,
              tooltip: getLoadTooltipRenderer()
            };
          }
          return series;
        }),
        axes: [
          prevOptions.axes[0],
          {
            ...prevOptions.axes[1],
            title: {
              text: currTab === "Load Wise" ? 'Load in Days' : 'Pending CCR Quantity',
              fontSize: 12,
              fontWeight: 300
            },
            crossLines: isLimitVisible ? [
              {
                type: "line",
                value: cwlValue,
                label: {
                  text: `Limit: ${cwlValue}`,
                  position: 'topRight',
                  color: '#820f4c',
                  fontSize: 10
                }
              },
            ] : []
          }
        ]
      };
    });
  }, [currTab, cwlValue]);

  // Update chart data when transformedData changes
  useEffect(() => {
    setChartOptions((prevOptions: any) => ({
      ...prevOptions,
      data: transformedData
    }));
  }, [transformedData]);

  // Add gray background using an area series approach - only if selectedAction is 'ANS'
  useEffect(() => {
    if (selectedAction === 'ANS' && horizonDateRange) {
      setChartOptions((prevOptions: any) => ({
        ...prevOptions,
        series: [
          {
            type: 'area',
            xKey: 'date',
            yKey: 'grayArea',
            yName:'Horizon',
            fill: 'rgba(200, 200, 200, 0.3)',
            stroke: 'none',
            visible: true,
            showInLegend: false,
            tooltip: { enabled: false },
            connectMissingData: false, 
          },
          ...prevOptions.series.filter((series: any) => series.yKey !== 'grayArea')
        ],
        data: transformedData.map((item: any) => ({
          ...item,
          grayArea: item.isInHorizonRange ? 8000 : null
        }))
      }));
    } else {
      setChartOptions((prevOptions: any) => ({
        ...prevOptions,
        series: prevOptions.series.filter((series: any) => series.yKey !== 'grayArea'),
        data: transformedData
      }));
    }
  }, [horizonDateRange, transformedData, currView]);

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollLeft = 0;
    }
  }, [currView]);

  const downloadChartWithHeader = () => {
    if (containerRef.current) {
      const chartCanvas = containerRef.current.querySelector('canvas');
      if (!chartCanvas) return;
      const headerHeight = 40;
      const combinedCanvas = document.createElement('canvas');
      combinedCanvas.width = chartCanvas.width;
      combinedCanvas.height = chartCanvas.height + headerHeight;
      const ctx = combinedCanvas.getContext('2d');
      if (!ctx) return;
      const titleText = `Future Order Load Chart`;
      ctx.font = 'bold 16px Arial';
      const textWidth = ctx.measureText(titleText).width;
      const xCoordinate = (combinedCanvas.width - textWidth) / 2;
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, combinedCanvas.width, headerHeight);
      ctx.fillStyle = 'black';
      ctx.fillText(titleText, xCoordinate, 25);
      ctx.drawImage(chartCanvas, 0, headerHeight);
      const link = document.createElement('a');
      link.href = combinedCanvas.toDataURL('image/png');
      link.download = titleText || 'chart.png';
      link.click();
    }
  };

  return (
    <GraphViewWrapper style={{ height: '80%' }}>
      <SCChartContainer
        height={'100%'}
        style={{
          border: '1px solid #CCCCCC',
          margin: '-10px',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div className="title" style={{ backgroundColor: 'white', height: '40px', display: 'flex', justifyContent: 'right', alignItems: 'center' }}>
          <div style={{ fontSize: '12px', margin: '0 auto', fontWeight: 500, textAlign: 'center' }}>
            Future Order Load Chart
          </div>
          <div style={{ display: 'flex' }}>
            <div style={{ paddingRight: '10px', cursor: "pointer" }} onClick={downloadChartWithHeader}>
              <img height={12} width={12} src="/assets/img/mto/RMPMBufferTrend/download.svg" alt="Download" />
            </div>
          </div>
        </div>
        <SCHorizontalDivider />
        <ApplyZoomOut style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', zoom: 0.6, paddingBottom: '10px' }}>
          <MyFutureOrderTabsFix>
            <VFFloatingTab
              handleClick={(e) => setCurrView(e.id)}
              tabs={Viewtabs}
              defaultTab={Viewtabs.findIndex((tab:any) => tab.id === currView) || 0}
            />
          </MyFutureOrderTabsFix>
        </ApplyZoomOut>
        <ChartWrapper>
          <div style={{ height: '100%', width: '100%' }} ref={containerRef}>
            <div className='chart-wrapper' style={{ flex: 1, height: "90%" }}>
              <CustomLegend chartOptions={chartoptions} setChartOptions={setChartOptions}/>
              <div className='chart-scroll'  ref={scrollContainerRef} style={{ overflowX: chartoptions?.data?.length > 15 ? "scroll" : "hidden", overflowY:'hidden' }}>
                <AgCharts ref={chartRef} style={{ height: "100%", width: chartoptions?.data?.length > 15 ? `${50*chartoptions?.data?.length + "px"}` : "100%" }} options={chartoptions} />
              </div>
            </div>
          </div>
        </ChartWrapper>
      </SCChartContainer>
    </GraphViewWrapper>
  );
};

export default GraphView;