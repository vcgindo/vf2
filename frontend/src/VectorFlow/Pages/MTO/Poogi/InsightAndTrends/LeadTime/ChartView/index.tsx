import moment from 'moment'
import { useState } from 'react'
import VFInfoToolTip from '../../../../../../../components/VectorFLOW/commons/VFInfoToolTip'
import { SCChartHeaderContainer, SCChartMainContainer } from '../../../../Common/SplitGraphContainer/styles'
import { useGetDate } from '../../../../../../Services/MTO/Production/InsightsAndTrends/RMPMExpediting'
import BoxPlotContainer from '../../../../Common/BoxPlotContainer'
import OverlayLoader from '../../../../../../../VectorFlow/Pages/MTO/Common/Loader'


const ChartView = ({ chartData, chartTableData }: any) => {

    const [tableLoading, setTableLoading] = useState(false);
    const [chartLoading, setChartLoading] = useState(false);
    const { data: apiResponseData, isLoading } = useGetDate();
    const date = apiResponseData?.data?.data;
    const graph1 = ['This box plot graph displays statistical distribution of lead time of closed orders. Each box represents the various statistical measures around lead time of closed orders.', 'Lead time = Closure date - Actual release date']
    const [hideChart1, toggleChart1] = useState(false);


    const generateHeader = () => {
        return (
            <>
                <SCChartMainContainer style={{ zoom: 1, width: '100%' }}>
                    <div
                        data-testid="otif-graph"
                        style={{
                            fontSize: "12px",
                            margin: "auto auto",
                            fontFamily: "Roboto",

                            textAlign: "center",
                        }}
                    >
                        <span style={{ fontWeight: 500 }}>Statistical Overview Of Lead Time Of Closed Orders &nbsp;</span>
                        <span style={{ fontWeight: 350 }}>{`(${moment(date).add(-90, 'days').format('D MMM YYYY')} - ${moment(date).format('D MMM YYYY')})`}</span>
                    </div>
                    <SCChartHeaderContainer>

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




    const boxChartOptions: any =
    {
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
                    lower: '#de7e2c',
                    upper: '#AD5000',

                }
            }
        }
        ,
        tooltip: {
            followCursor: false,
            enabledOnSeries: [1]
        }
    }


    const columnDefinitions = [
        {
            headerName: 'Week',
            field: 'week',
            resizable: true,
        },
        {
            headerName: 'LW',
            field: 'lw',
            resizable: true,
        },
        {
            headerName: 'Q1',
            field: 'q1',
            resizable: true,
        },
        {
            headerName: 'Q2',
            field: 'q2',
            resizable: true,
        },
        {
            headerName: 'Q3',
            field: 'q3',
            resizable: true,
        },
        {
            headerName: 'HW',
            field: 'uw',
            resizable: true,
        },
    ];

    const boxSeries = [{
        name: 'elapsed time',
        type: 'boxPlot',
        data: chartData
    }]



    return (
        <div style={{ height: "90%", paddingBottom: '20px', marginLeft: '20px', paddingTop: '20px', display: 'flex' }}>
            {isLoading && <OverlayLoader />}

            <BoxPlotContainer
                tableLoading={tableLoading}
                chartLoading={chartLoading}
                setTableLoading={setTableLoading}
                setChartLoading={setChartLoading}
                rowData={chartTableData}
                boxChartData={chartData}
                boxChartOptions={boxChartOptions}
                graphTitle={''}
                tableTitle={`Statistical Overview Of Lead Time Of Closed Orders`}
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

export default ChartView