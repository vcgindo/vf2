import moment from 'moment'
import { useState, useEffect } from 'react'
import VFInfoToolTip from '../../../../../../../components/VectorFLOW/commons/VFInfoToolTip'
import { SCChartHeaderContainer, SCChartMainContainer } from '../../../../Common/SplitGraphContainer/styles'
import { useGetDate } from '../../../../../../Services/MTO/Production/InsightsAndTrends/RMPMExpediting'
import BoxPlotContainer from '../../../../Common/BoxPlotContainer'
import { useGetDeptMasterData, useGetPlantMasterData } from '../../../../../../../VectorFlow/Services/MTO/Common/Masters'
import RadioSelect from '../../../../../../../components/VectorFLOW/commons/MTO/RadioSelect'
import { useUserData } from '../../../../../../../context'
import VFButton from '../../../../../../../components/VectorFLOW/commons/VFButton'

const WeekWiseGraph = ({ handleSelectionChange, chartTableData, chartData, plant, dept }: any) => {

    const { mutateAsync: getPlantMasterData } = useGetPlantMasterData();
    const { mutateAsync: getDeptMasterData } = useGetDeptMasterData();
    const [hideChart1, toggleChart1] = useState(false);
    const [selectOptionsDep, setSelectOptionsDep] = useState([])
    const [selectOptionsPlnt, setSelectOptionsPlnt] = useState([])
    const [depOpts, setDepOpts] = useState([]);
    const [plntOpts, setPlntOpts] = useState([]);
    const [tableLoading, setTableLoading] = useState(false);
    const [chartLoading, setChartLoading] = useState(false);

    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;

    const [selectedPlant, setSelectedPlant] = useState(plant);
    const [selectedDept, setSelectedDept] = useState(dept);



    const { data: apiResponseData, /*isLoading, refetch*/ } = useGetDate();

    const date = apiResponseData?.data?.data;

    const getPlntData = async () => {
        try {

            const result = await getPlantMasterData();
            setPlntOpts(result?.data?.data);
        }
        catch (error) {
            console.log(error)
        }
    }

    const getDeptData = async () => {
        try {

            const result = await getDeptMasterData();
            setDepOpts(result?.data?.data);
        }
        catch (error) {
            console.log(error)
        }
    }

    useEffect(() => {
        getPlntData();
        getDeptData();
    }, [])


    useEffect(() => {

        const newPlantOptions: any = [];

        plntOpts?.forEach &&
            plntOpts?.forEach((e: any) => {
                const eachPlant = { value: e.plant_id, label: e.plant_name }

                newPlantOptions.push(eachPlant);
            })

        setSelectOptionsPlnt(newPlantOptions);

        const newDepOptions: any = [];

        depOpts?.forEach &&
            depOpts?.forEach((e: any) => {
                const eachDep = { value: e.dept_id, label: e.dept_name }

                newDepOptions.push(eachDep);
            })

        setSelectOptionsDep(newDepOptions);
    }, [plntOpts, depOpts])

    const graph1 = ['This box plot graph highlights the trend of statistical distribution of elapsed time for the selected plant-department']

    const handleSubmitClick = () => {
        handleSelectionChange(selectedPlant, selectedDept)
    }

    const generateHeader = () => {
        return (
            <>
                <SCChartMainContainer style={{ zoom: 1, width: '100%' }}>
                    <div
                        data-testid="otif-graph"
                        style={{
                            fontSize: "12px",
                            margin: "auto auto auto 0",
                            fontFamily: "Roboto",
                            textAlign: "center",
                            display: 'flex',
                            gap: '10px'
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', marginLeft: '10px' }}>
                            <p style={{ fontWeight: 'bold', paddingRight: '5px' }}>Plant </p>
                            <RadioSelect theme={themeUi} options={selectOptionsPlnt} value={selectedPlant} onChange={(newValue: any) => { setSelectedPlant(newValue) }} />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                            <p style={{ fontWeight: 'bold', paddingRight: '5px' }}>Department </p>
                            <RadioSelect theme={themeUi} options={selectOptionsDep} value={selectedDept} onChange={(newValue: any) => { setSelectedDept(newValue) }} />
                        </div>
                        <VFButton
                                onClick={() => handleSubmitClick()}
                                themeUi={themeUi}
                                disabled={false}
                                style={{
                                    height: '30px',
                                    width: '40px', 
                                    borderRadius: '3px',
                                }}
                            >
                                <img
                                    src="/assets/img/rightArrowHorizontal.svg"
                                    height={13}
                                    width={7}
                                />
                        </VFButton>
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
            export: {
                csv: {
                    filename: `Elapsed Time Trend: Statistical Distribution For The Selected Department`,
                },
                svg: {
                    filename: `Elapsed Time Trend: Statistical Distribution For The Selected Department`,
                },
                png: {
                    filename: `Elapsed Time Trend: Statistical Distribution For The Selected Department`,
                }
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
                formatter: (val: any) => {
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
            enabledOnSeries: [1]
        }
    }

    // const chartData: any = [
    //     { x: "Feb 2024", y: [2, 5, 8, 11, 14] },
    //     { x: "Mar 2024", y: [2, 3, 5, 6, 8] },
    //     { x: "May 2024", y: [1, 3, 4, 5, 9] },
    //     { x: "Jun 2024", y: [2, 4, 6, 8, 10] },
    //     { x: "July 2024-WK 1", y: [3, 5, 7, 9, 11] },
    //     { x: "July 2024-WK 2", y: [3, 5, 7, 9, 11] },
    //     { x: "July 2024-WK 3", y: [3, 5, 7, 9, 11] },
    //     { x: "July 2024-WK 4", y: [3, 5, 7, 9, 11] },
    //     { x: "Aug 2024-WK 1", y: [3, 6, 9, 12, 15] },

    // ];


    // const chartTableData = [
    //     { 'week': 'Jul2024-Wk1', 'LW': 1, 'Q1': 3, 'Q2': 4, 'Q3': 7, 'HW': 9 },
    //     { 'week': 'Jul2024-Wk2', 'LW': 2, 'Q1': 4, 'Q2': 5, 'Q3': 8, 'HW': 10 },
    //     { 'week': 'Jul2024-Wk3', 'LW': 3, 'Q1': 5, 'Q2': 6, 'Q3': 9, 'HW': 11 },
    //     { 'week': 'Jul2024-Wk4', 'LW': 4, 'Q1': 6, 'Q2': 7, 'Q3': 10, 'HW': 12 },
    //     { 'week': 'Aug2024-Wk1', 'LW': 5, 'Q1': 7, 'Q2': 8, 'Q3': 11, 'HW': 13 },
    //     { 'week': 'Aug2024-Wk2', 'LW': 6, 'Q1': 8, 'Q2': 9, 'Q3': 12, 'HW': 14 },
    //     { 'week': 'Aug2024-Wk3', 'LW': 7, 'Q1': 9, 'Q2': 10, 'Q3': 13, 'HW': 15 },
    // ]




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
        <div style={{ height: "100%", paddingBottom: '10px', display: 'flex', justifyContent: 'left', marginLeft: '12px' }}>


            <BoxPlotContainer
                tableLoading={tableLoading}
                chartLoading={chartLoading}
                setTableLoading={setTableLoading}
                setChartLoading={setChartLoading}
                boxChartData={chartData}
                boxChartOptions={boxChartOptions}
                rowData={chartTableData}
                graphTitle={`Elapsed Time Trend: Statistical Distribution For The Selected Department`}
                tableTitle={`Elapsed Time Trend: Statistical Distribution For The Selected Department`}
                dateStr={`(${moment(date).subtract(90, 'days').format('D MMM YYYY')} - ${moment(date).format('D MMM YYYY')})`}
                colDef={columnDefinitions}
                header={generateHeader}
                hideChart={hideChart1}
                toggleChart={toggleChart1}
                graphType={10}
                boxChartSeries={boxSeries}
            />
        </div>
    )
}

export default WeekWiseGraph