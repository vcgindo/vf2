import React, { useRef, useState } from "react";
import "allotment/dist/style.css";
import {
    SCChartContainer, SCHorizontalDivider
} from '../styles';
import { AgCharts } from "ag-charts-react";
import { AgChartOptions } from "ag-charts-community";
import { InsightsAndTrendsString } from "../../../../Common/String";
import { ProcurementSeriesDataFill, ProcurementSeriesDataYKey, ProcurementSeriesDataYName } from "../../../../Common/Enum";
import VFInfoToolTip from "../../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import VFModalCard from "../../../../../../../components/VectorFLOW/commons/VFModalCard";
import VFTable from "../../../../Common/VFTable";
import { GridRef } from "../../../../../../../VectorFlow/types/MDM";
import { useGetDate } from "../../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting";
import moment from "moment";
import _ from "lodash";
import { ChartWrapper, GraphViewWrapper } from "./styles";

const GraphView = ({ shortageData }: any) => {

    const { data: apiResponseData, isSuccess } = useGetDate();
    const [apiDate, setApiDate] = useState(apiResponseData?.data?.data);
    const [date, setDate] = useState('');

  const containerRef  = useRef<HTMLDivElement>(null);


      const downloadChartWithHeader = () => {
        if (containerRef.current) {
          const chartCanvas = containerRef.current.querySelector('canvas');
          if (!chartCanvas) {
            console.error("Chart canvas not found.");
            return;
          }
    
          const headerHeight = 40;
          const combinedCanvas = document.createElement('canvas');
          combinedCanvas.width = chartCanvas.width;
          combinedCanvas.height = chartCanvas.height + headerHeight;
    
          const ctx = combinedCanvas.getContext('2d');
          if (!ctx) {
            console.error("Failed to get canvas context.");
            return;
          }
    
          const titleText = `RM / PM Orderwise Coverage ( ${date})`
    
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


    React.useEffect(() => {
        setApiDate(apiResponseData?.data?.data);
    }, [apiResponseData]);

    React.useEffect(() => {
        if (apiDate) {
            setDate(`${moment(apiDate).format('D MMM YYYY')} - ${moment(apiDate).add(90, 'days').format('D MMM YYYY')}`);
        }
    }, [apiDate, isSuccess]);

    function TooltipRenderer({ datum, xKey }: any) {
        return `
    <div class="ag-chart-tooltip-title" style="background-color: #6C696A; display: flex; justify-content: center; align-items: center">
        ${isNaN(datum[xKey]) ? `${datum[xKey]} Days` :(datum[xKey] === 1) ? '0-7 Days' : (datum[xKey] === 85) ? '85-90 Days' : (datum[xKey] + '-' + (Number(datum[xKey] + 6)) + ' Days')}
    </div>
    <div class="ag-chart-tooltip-content" style="color: white; background-color: #6C696A">
    
    <div>
        <div style="display: flex;">
            <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #F4BD8E">
            </div>
            <div style="display:flex ; width: 100%; justify-content: space-between">
                <div>${InsightsAndTrendsString.ordersWithFullkitOHS}
                </div>
                <div> ${datum['total_soh']}
                </div>
            </div>
        </div>
        <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color:#F09241"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>${InsightsAndTrendsString.ordersWithFullkitSIT}</div><div>${datum["total_sit"]}</div></div></div>
        <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color:  #AD5000"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>${InsightsAndTrendsString.ordersWithFullkitOPO}</div><div>${datum["total_po"]}</div></div></div>
        <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #6A3001"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>${InsightsAndTrendsString.ordersWithRMPM}</div><div> ${datum["shortage"]}</div></div></div>
    </div>`
    }


    function createSeriesData(val: number) {
        const seriesData: any = [];
        for (let i = 0; i < val; i++) {
            seriesData.push(
                {
                    "type": "bar",
                    "xKey": "start_date",
                    "yKey": ProcurementSeriesDataYKey[i],
                    "yName": ProcurementSeriesDataYName[i],
                    "stacked": true,
                    "strokeOpacity": 0,
                    "strokeWidth": 2,
                    "fill": ProcurementSeriesDataFill[i],
                    "tooltip": {
                        renderer: TooltipRenderer
                    },
                }
            )
        }

        return seriesData;
    }

    const numberOfSeriesData = 4;
    const seriesData = createSeriesData(numberOfSeriesData);
    const options: AgChartOptions = ({

        data: shortageData, // Todo final data
        series: seriesData,
        axes: [
            {
                type: "category",
                position: 'bottom',
                title: { text: "Timeline For Upcoming Order Releases", fontSize: 10, fontWeight: "bold" },
                label: {

                    fontSize: 8,
                    fontWeight: 'bold',
                    color: 'black',
                    formatter: (params) => {
                        if (params.value === '1') {
                            return '0-7 Days'
                        }
                        else if (params.value === '85') {
                            return '85-90 Days'
                        }
                        else {
                          const categoryLable =  isNaN(Number(params.value)) ? params.value : `${params.value}-${Number(params.value) + 6} Days` ;
                          const categoryLableLength = categoryLable.length > 20 ? categoryLable.slice(0, 19) + "..." : categoryLable; 

                            return categoryLableLength;
                        }

                    }
                },
                gridLine: {
                    enabled: false
                }
            },
            {
                title: { text: "Count of Orders", fontSize: 10, fontWeight: "bold", spacing: 3 },
                type: "number",
                line: { enabled: true },
                position: 'left',
                label: {
                    fontSize: 8,
                    fontWeight: 'bold',
                    color: 'black',

                },
                gridLine: {
                    enabled: false
                }
            }
        ],

        legend: {
            item: {
                label: {
                    fontSize: 10
                }         
            }
        },
    });

    const TableData = _.cloneDeep(shortageData);
    TableData?.forEach((e: any) => {
        if (e.start_date === '1') {
            e.start_date = '0-7 Days';
        }
        else {
            e.start_date = e.start_date + '-' + (Number(e.start_date) + 6) + ' Days';
        }
    })

    const refGraph1 = useRef<GridRef>(null);

    const chartRef = useRef<any>(null);
    const [hideChart1, toggleChart1] = useState(false);
    const ColdDefs = [
        {
            colId: 'start_date',
            field: 'start_date',
            headerName: 'Days Range',
        },
        {
            colId: 'total_soh',
            field: 'total_soh',
            headerName: 'Stock On hand',
        },
        {
            colId: 'total_sit',
            field: 'total_sit',
            headerName: 'Stock In (Transit + QC)',
        },
        {
            colId: 'total_po',
            field: 'total_po',
            headerName: 'Open Orders',
        },
        {
            colId: 'shortage',
            field: 'shortage',
            headerName: 'rmpm Shortage',
        },

    ]

    const myCustomTheme: any = {
        palette: {
            fills: ['#F4BD8E', '#F09241', ' #AD5000', '#6A3001'],
            strokes: ['#F4BD8E', '#F09241', ' #AD5000', '#6A3001'],
        },
    }

    const generateChart = () => {
        refGraph1.current?.api.createRangeChart({
            chartType: 'stackedColumn',
            cellRange: {
                columns: ['total_soh', 'total_sit', 'total_po', 'shortage'],
            },

            chartThemeOverrides: {
                bar: {
                    axes: {
                        category: {
                            gridLine: { enabled: true },

                            bottom: {
                                label: {
                                    fontSize: 8,

                                }
                            }
                        }
                    },
                    series: {
                        highlightStyle: {
                            item: {
                                fill: 'white',
                                fillOpacity: 0.2,
                            }
                        },
                        tooltip: {
                            renderer: TooltipRenderer
                        },
                        strokeWidth: 1,
                        strokeOpacity: 0,


                    },
                    legend: {

                        item: {
                            label: {
                                fontSize: 10
                            },

                            marker: {
                                shape: 'square'
                            }
                        }
                    },
                }

            }
        })
    }

    return (
        <GraphViewWrapper>
            <SCChartContainer height={'100%'} style={{ border: '1px solid #CCCCCC', margin: '2px', height: '100%', display: 'flex', flexDirection: 'column' }}>
                <div className="title" style={{ backgroundColor: 'white', height: '40px', display: 'flex', justifyContent: 'right', alignItems: 'center' }}>
                    <div style={{ fontSize: '12px', margin: '0 auto', fontWeight: 500, textAlign: 'center' }}>
                        {`${InsightsAndTrendsString.rmpmOrderwiseCoverage}  (${date})`}
                    </div>
                    <div style={{ display: 'flex' }}>
                        <div style={{ marginLeft: 30, marginBottom: '-5px' }}>
                            <VFInfoToolTip infoList={['The graph highlights the Full kit position of Raw material and Packing material of unreleased orders.']} />
                        </div>
                        <div onClick={() => { toggleChart1(!hideChart1) }} style={{ marginLeft: 10, marginBottom: '-5px', marginRight: '10px', cursor:"pointer" }}>
                            <img src='/assets/img/VectorFLOW/BPR/minimize.svg' height={13} width={13} color={"#CCCCCC"} />
                        </div>
                    </div>
                </div>

                <SCHorizontalDivider />

                <ChartWrapper>
                    <div style={{ height: '100%', width: '100%' }} ref={containerRef}>
                        <div style={{ display: 'flex', justifyContent: "right" }}>

                            <div style={{ paddingRight: '10px', cursor:"pointer" }} onClick={downloadChartWithHeader}
                            > <img height={12} width={12} src="/assets/img/mto/RMPMBufferTrend/download.svg" /></div>
                        </div>

                        <div className='chart-wrapper' style={{ flex: 1, height: "90%" }}>
                            <AgCharts ref={chartRef} options={options} />
                        </div>
                    </div>
                </ChartWrapper>

                <VFModalCard openModal={hideChart1} closeModal={() => toggleChart1(false)} headerIcon='' headerText={`RM / PM Orderwise Coverage ( ${date})`} headerBgColor="" headerTextColor="#00000" paddingLeftAndRight={27} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}>
                    <div className="ag-theme-planning" style={{ width: '1000px' }}>
                        <VFTable

                            ref={refGraph1}
                            columnDefs={ColdDefs}
                            // rowData={sortData(convertToInt(data['maxTechBlackRedColumn']['data']))}
                            rowData={TableData}
                            enableCharts={true}
                            enableRangeSelection={true}
                            rowSelection="multiple"

                            statusBar={{
                                statusPanels: [
                                    { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                                    { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                                    { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                                    { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                                    { statusPanel: 'agAggregationComponent', align: 'left' },
                                ],
                            }} onGridReady={() => { generateChart() }}
                            // getChartToolbarItems={getChartToolbarItems}
                            chartToolPanelsDef={
                                {
                                    panels: []
                                }
                            }
                            // chartThemeOverrides={chartThemeOverridesG1}
                            chartThemes={['myCustomTheme']}
                            customChartThemes={{
                                'myCustomTheme': myCustomTheme
                            }}
                            disableZoomScaling={true}
                            defaultColDef={{
                                floatingFilter: true,
                                filter: "agMultiColumnFilter",
                                flex: 1
                            }}
                            height={'480px'}
                        />
                    </div>
                </VFModalCard>
            </SCChartContainer>
        </GraphViewWrapper>

    )
};

export default GraphView;
