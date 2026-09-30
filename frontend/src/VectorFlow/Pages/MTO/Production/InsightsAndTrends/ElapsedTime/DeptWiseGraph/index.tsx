import moment from 'moment'
import { useState } from 'react'
import VFInfoToolTip from '../../../../../../../components/VectorFLOW/commons/VFInfoToolTip'
import { SCChartHeaderContainer, SCChartMainContainer } from '../../../../Common/SplitGraphContainer/styles'
import { useGetDate } from '../../../../../../Services/MTO/Production/InsightsAndTrends/RMPMExpediting'
import BoxPlotContainer from '../../../../Common/BoxPlotContainer'

const DeptWiseGraph = ({chartTableData, chartData, alertData}: any) => {

    const graph1 = ['This box plots highlights the statistical distribution of dept-wise elapsed time (in days) for orders closed in the last 7 days at respective departments.',
        'The box plots in Red indicate that the median elapsed time in those departments have increased by more than 15% (last week vs prev. 4 weeks). '
    ]

    const [hideChart1, toggleChart1] = useState(false);


    const generateHeader = () => {
        return (
            <>
                <SCChartMainContainer style={{ zoom: 1, width: '100%' }}>

                    <SCChartHeaderContainer style={{ width: '100%', display: 'flex', justifyContent: 'end' }}>

                        <div style={{ marginLeft: 30, marginBottom: '-5px' }}>
                            <VFInfoToolTip infoList={graph1} />
                        </div>
                        <div onClick={() => { toggleChart1(!hideChart1) }} style={{ marginLeft: 10, marginBottom: '-5px', marginRight: '10px' }}>
                            <img src='/assets/img/VectorFLOW/BPR/minimize.svg' height={13} width={13} color={"#CCCCCC"} />
                        </div>
                    </SCChartHeaderContainer>
                </SCChartMainContainer>
            </>

        )
    }

    const [tableLoading, setTableLoading] = useState(false);
    const [chartLoading, setChartLoading] = useState(false);
    const { data: apiResponseData, /*isLoading, refetch*/ } = useGetDate();
    const date = apiResponseData?.data?.data;
    const boxChartOptions: any = {
        theme: {
            monochrome: {
                enabled: true,
                color: '#FF0000',
                shadeIntensity: 0
            },
            palette: 'palette4',
        },
        chart: {
            type: 'boxPlot',

            zoom: {
                enabled: false,
            },
            toolbar: {
                show: true,
                tools: {
                    download: '<img src="/assets/img/mto/RMPMBufferTrend/download.svg" class="ico-download" width="14">',
                    customIcons: [],
                },
            },
        },

        grid: {
            show: false,

        },
        legend: {
            show: false

        }
        ,
        stroke: {
            show: true,
            curve: 'smooth',
            lineCap: 'butt',
            colors: ['#848484'],
            width: 1.5,
            dashArray: 0
        },
        xaxis: {
            crosshairs: {
                show: false
            },
            tooltip: {
                enabled: false,
            },

            labels: {
                
                rotateAlways: true,
                style: {
                    fontSize: '12px', // Font size of y-axis labels
                    fontFamily: 'Roboto', // Font family of y-axis labels
                    colors: '#717171',
                    fontWeight: 400
                },
            },
        },
        yaxis: {
            axisBorder: {

                show: true
            },
            title: {
                text: 'Elapsed Time (in Days)',
                style: {
                    fontSize: '12px',
                    fontFamily: 'Roboto',
                    color: '#6d6d6d'
                },
            },
            labels: {

                formatter: (val:any)=>{
                    return parseFloat(val.toFixed(2))
                },


                style: {
                    fontSize: '10px',
                    fontWeight: 'bold', // Font size of y-axis labels
                    fontFamily: 'Roboto', // Font family of y-axis labels
                    colors: '#717171'
                },
            },

        },
        // colors: ['red'],

        plotOptions: {

            boxPlot: {
                colors: {
                    lower: '#D3D3D3',
                    upper: '#848484',

                }
            }
        }
        ,
        tooltip: {
            followCursor: false,
            // enabled: true,
            // enabledOnSeries: []

        }
    }
    // const chartData: any = [
    //     { x: "P2-Dept 2", y: [2, 5, 8, 11, 14] },
    //     { x: "P3-Dept 3", y: [2, 3, 5, 6, 8] },
    //     { x: "P4-Dept 4", y: [1, 3, 4, 5, 9] },
    //     { x: "P5-Dept 5", y: [2, 4, 6, 8, 10] },
    //     { x: "P6-Dept 6", y: [3, 5, 7, 9, 11] },
    //     { x: "P9-Dept 9", y: [3, 6, 9, 12, 15] },
    //     { x: "P10-Dept 10", y: [4, 7, 10, 13, 16] }
    // ];

    // const chartTableData = [
    //     { dept: 'P1-Dept1', LW: 2, Q1: 4, Q2: 5, Q3: 7, HW: 9 },
    //     { dept: 'P2-Dept2', LW: 3, Q1: 5, Q2: 6, Q3: 8, HW: 10 },
    //     { dept: 'P3-Dept3', LW: 1, Q1: 3, Q2: 4, Q3: 6, HW: 7 },
    //     { dept: 'P4-Dept4', LW: 4, Q1: 6, Q2: 7, Q3: 9, HW: 11 },
    //     { dept: 'P5-Dept5', LW: 2, Q1: 4, Q2: 5, Q3: 7, HW: 9 },
    //     { dept: 'P6-Dept6', LW: 5, Q1: 7, Q2: 8, Q3: 10, HW: 12 }
    // ];

    const columnDefinitions = [
        { headerName: 'Department', field: 'department' },
        { headerName: 'LW', field: 'lw' },
        { headerName: 'Q1', field: 'q1' },
        { headerName: 'Q2', field: 'q2' },
        { headerName: 'Q3', field: 'q3' },
        { headerName: 'HW', field: 'uw' }
    ];

    const boxSeries = [{
        name: 'elapsed time',
        type: 'boxPlot',
        data: chartData
    }, {
        name: 'Alert',
        type: 'scatter',
        data: alertData
        // data: [
        //     { x: "P2-Dept 2", y: [16] },
        //     { x: "P2-Dept 3", y: [] },
        //     { x: "P2-Dept 4", y: [10] }
        // ]
    }]


    return (
        <div style={{ height: "100%", paddingBottom: '10px', display: 'flex', justifyContent: 'left', marginRight: '4px' }}>


            <BoxPlotContainer
                tableLoading={tableLoading}
                chartLoading={chartLoading}
                setTableLoading={setTableLoading}
                setChartLoading={setChartLoading}
                rowData={chartTableData}
                boxChartData={chartData}
                boxChartOptions={boxChartOptions}
                graphTitle={`Department-Wise Elapsed Time Distribution For Closed Orders`}
                tableTitle={`Department-Wise Elapsed Time Distribution For Closed Orders`}
                dateStr={`(${moment(date).format('D MMM YYYY')})`}
                colDef={columnDefinitions}
                header={generateHeader}
                hideChart={hideChart1}
                toggleChart={toggleChart1}
                graphType={11}
                boxChartSeries={boxSeries}
            />

        </div>
    )
}

export default DeptWiseGraph