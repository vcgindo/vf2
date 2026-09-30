import { useEffect, useState } from 'react'
import VFInfoToolTip from '../../../../../../../components/VectorFLOW/commons/VFInfoToolTip'
import VFCapsule from '../../../../../../../components/VectorFLOW/commons/VFCapsule'
import VFRangeSlider from '../../../../../../../VectorFlow/Pages/MTO/Common/VFRangeSlider'
import { CapsuleWrapper } from '../../RMPMOrderwiseCoverage/GraphView/styles'
import { SCChartHeaderContainer, SCChartMainContainer, SCChartSliderContainer } from '../../styles'
import SplitGraphContainer from '../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer'
import { useGetDate } from '../../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting'
import moment from 'moment'
import { useUserData } from '../../../../../../../context'
import VFButton from '../../../../../../../components/VectorFLOW/commons/VFButton'


const BTMTA = ({ isMTO, data, lastRunDate}: { isMTO: boolean, data: any, lastRunDate: Date }) => {

    console.log(isMTO)

    const [chartLoading, setChartLoading] = useState(false);
    const [tableLoading, setTableLoading] = useState(false);
    const [horizonDays, setHorizondays] = useState(14);

    useEffect(() => {
        setNumericData(filterDataByDaysGap(data, 0, horizonDays, false))
    }, [data])

    const [numericData, setNumericData] = useState<BufferTrendData[]>([]);


    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;

    const TooltipRenderer = ({ datum, xKey }: any) => {
        let countArr = [];
        let perArr = [];
        function convertToPercentageArray(absoluteValues: number[]) {
            const total = absoluteValues.reduce((sum, value) => sum + value, 0);
            if (total === 0) {
                return absoluteValues.map(() => 0);
            }
            const percentageValues = absoluteValues.map(value => (value / total) * 100);
            return percentageValues;
        }
        if (actBtn.label === 'Absolute Value') {
            countArr = [datum['b'], datum['r'], datum['y'], datum['g'], datum['w']]
            perArr = convertToPercentageArray(countArr);
        }
        else {
            perArr = [datum['b'], datum['r'], datum['y'], datum['g'], datum['w']];
            let reqData = null;
            countArr = [0, 0, 0, 0, 0];
            data.forEach((element: any) => {
                if (element.dt === datum['dt']) {
                    reqData = element;
                    countArr = [reqData.b, reqData.r, reqData.y, reqData.g, reqData.w]
                }
            });
        }
        return `
      

        <div style="background:#6C696A" >
        <div  style=" color: white; padding-top: 10px; padding-bottom:4px;background-color: #6C696A; display: flex; justify-content: center; align-items: center">
            ${datum[xKey]}
        </div>
        <div style="color: white; background-color: #6C696A; padding: 10px"><table style="width: 100%; color: white; border-collapse: collapse;">
            <thead style="border-bottom: 1px dashed white; border-top: 1px dashed white">
                <tr><th style="padding: 5px;  background-color: #6C696A; text-align: left; width: 120px"></th><th style="font-size: 8px; padding: 5px;  background-color: #6C696A; text-align: right;">Percentage</th><th style="font-size: 8px; padding: 5px;  background-color: #6C696A; text-align: right;">Count</th></tr></thead>
            <tbody>
            <tr><td style="padding: 5px; background-color: #6C696A;"><div style="display: flex; align-items: center;"><div style="margin-right: 10px; height: 3px; width: 15px; background-color: black"></div>Black</div></td>
                <td style="padding: 5px; background-color: #6C696A;">${Math.round(perArr[0])}%</td>
                <td style="padding: 5px; background-color: #6C696A;">${countArr[0]}</td></tr>
            <tr><td style="padding: 5px; background-color: #6C696A;"><div style="display: flex; align-items: center;"><div style="margin-right: 10px; height: 3px; width: 15px; background-color: red"></div>Red</div></td>
                <td style="padding: 5px; background-color: #6C696A;">${Math.round(perArr[1])}%</td>
                <td style="padding: 5px; background-color: #6C696A;">${countArr[1]}</td></tr>
            <tr><td style="padding: 5px; background-color: #6C696A;"><div style="display: flex; align-items: center;"><div style="margin-right: 10px; height: 3px; width: 15px; background-color: yellow"></div>Yellow</div></td>
                <td style="padding: 5px; background-color: #6C696A;">${Math.round(perArr[2])}%</td>
                <td style="padding: 5px; background-color: #6C696A;">${countArr[2]}</td></tr>
            <tr><td style="padding: 5px; background-color: #6C696A;"><div style="display: flex; align-items: center;"><div style="margin-right: 10px; height: 3px; width: 15px; background-color: green"></div>Green</div></td>
                <td style="padding: 5px; background-color: #6C696A;">${Math.round(perArr[3])}%</td>
                <td style="padding: 5px; background-color: #6C696A;">${countArr[3]}</td></tr>
            <tr><td style="padding: 5px; background-color: #6C696A;"><div style="display: flex; align-items: center;"><div style="margin-right: 10px; height: 3px; width: 15px; background-color: grey"></div>White</div></td>
                <td style="padding: 5px; background-color: #6C696A;">${Math.round(perArr[4])}%</td>
                <td style="padding: 5px; background-color: #6C696A;">${countArr[4]}</td></tr>
            </tbody> </table>
        </div>
        </div>
        `;
    }

    type BufferTrendData = {
        dt: string;
        b: number;
        r: number;
        g: number;
        y: number;
        w: number;
    };




    function filterDataByDaysGap(
        buffData: BufferTrendData[] | undefined,
        numberOfDaysGap: number,
        horizonDays: number,
        isPer: boolean
    ): BufferTrendData[] {
        if (!buffData || buffData.length === 0) {
            return []; // Return empty array if data is undefined or empty
        }

        buffData = isPer ? convertToPercentage(buffData) : buffData;

        const sortedData = buffData.slice().sort((a, b) => {
            // Ensure dt is defined before accessing split
            const dateA = a.dt ? new Date(a.dt.split('-').reverse().join('-')) : null;
            const dateB = b.dt ? new Date(b.dt.split('-').reverse().join('-')) : null;
            return dateA && dateB ? dateB.getTime() - dateA.getTime() : 0;
        });

        const filteredData: BufferTrendData[] = [];
        let currentDate: Date | null = null;

        sortedData.forEach(item => {
            if (item.dt) {
                const itemDate = new Date(item.dt.split('-').reverse().join('-'));
                if (!currentDate || (currentDate.getTime() - itemDate.getTime()) >= numberOfDaysGap * 24 * 60 * 60 * 1000) {
                    filteredData.push(item);
                    currentDate = itemDate;
                }
            }
        });

        // Slice the filtered data to keep the end date fixed
        const result = filteredData.reverse().slice(-horizonDays);
        return result;
    }


    function convertToPercentage(data: BufferTrendData[]): BufferTrendData[] {
        return data.map(entry => {
            const total = entry.b + entry.r + entry.g + entry.y + entry.w;
            if (total === 0) {
                return entry
            }
            return {
                dt: entry.dt,
                b: ((entry.b / total) * 100),
                r: ((entry.r / total) * 100),
                g: ((entry.g / total) * 100),
                y: ((entry.y / total) * 100),
                w: ((entry.w / total) * 100),
            };
        });
    }
    const [actBtn, setActBtn] = useState({
        label: "Absolute Value",
        value: 'Absolute Value'
    })

    function convertDate(dateStr: string): string {
        // Split the input string by spaces
        const [monthStr, dayStr, yearStr] = dateStr.split(' ');

        // Remove the 'th', 'st', 'nd', 'rd' from the day string
        const day = dayStr.replace(/\D/g, '');

        // Reformat the date to "29-Aug-24"
        return `${day}-${monthStr}-${yearStr}`;
    }


    const options: any = {
        axes: [
            {
                type: "category",
                position: 'bottom',
                label: {
                    fontSize: 8,
                    color: 'black',
                    avoidCollisions: true,
                    autoRotate: false,
                    formatter: function (params: any) {
                        const myDate = params.value.split('-')[1] + '-' + params.value.split('-')[0] + '-' + params.value.split('-')[2];
                        return convertDate(moment(myDate).format("MMM Do YY"))
                    }
                },
                gridLine: {
                    enabled: false
                }
            },
            {
                title: {
                    formatter: () => {
                        if (actBtn.label === 'Absolute Value') {
                            return 'SKU Locations'
                        }
                        return "Percentage of SKU Locations"
                    }, text: "Percentage of SKU Locations", fontSize: 10, spacing: 3
                },
                type: "number",
                line: { enabled: true },
                position: 'left',
                label: {
                    formatter: function (params: any) {
                        return (params.value) + ((actBtn.label === 'Percentage') ? '%' : '');
                    },
                    fontSize: 8,
                    color: 'black',

                },
                gridLine: {
                    enabled: false
                }
            }
        ],
        series: [
            {
                type: "line",
                xKey: "dt",
                yKey: "b",
                yName: "Black",
                stroke: "black",
                strokeWidth: 3,
                marker: {
                    fill: "Black",
                    stroke: "Black",
                    formatter: function (params: any) {
                        if (params.datum.b === 0) return { size: 0 }
                    }
                },
                tooltip: {

                    renderer: TooltipRenderer

                }
            },
            {
                type: "line",
                xKey: "dt",
                xName: "Date",
                yKey: "r",
                strokeWidth: 3,
                yName: "Red",
                stroke: "Red",
                marker: {
                    fill: "Red",
                    stroke: "Red",
                    formatter: function (params: any) {
                        if (params.datum.r === 0) return { size: 0 }
                    }

                },
                tooltip: {

                    renderer: TooltipRenderer

                }

            },
            {
                type: "line",
                xKey: "dt",
                strokeWidth: 3,
                xName: "Date",
                yKey: "y",
                yName: "Yellow",
                stroke: "Yellow",
                marker: {
                    fill: "#FFBF00",
                    stroke: "#FFBF00",
                    formatter: function (params: any) {
                        if (params.datum.y === 0) return { size: 0 }
                    }
                },
                tooltip: {

                    renderer: TooltipRenderer

                }
            },
            {
                type: "line",
                xKey: "dt",
                strokeWidth: 3,
                xName: "Date",
                yKey: "g",
                yName: "Green",
                stroke: "Green",
                marker: {
                    fill: "Green",
                    stroke: "Green",
                    formatter: function (params: any) {
                        if (params.datum.g === 0) return { size: 0 }
                    }
                },
                tooltip: {

                    renderer: TooltipRenderer

                }

            }
            ,
            {
                type: "line",
                xKey: "dt",
                xName: "Date",
                yKey: "w",
                yName: "White",
                stroke: "Grey",
                strokeWidth: 3,
                marker: {
                    fill: "grey",
                    stroke: "grey",
                    formatter: function (params: any) {
                        if (params.datum.w === 0) return { size: 0 }
                    }
                },
                tooltip: {

                    renderer: TooltipRenderer

                }
            }

        ],
        legend: {
            position: 'bottom',
            item: {
                label: {
                    fontSize: 10,
                    fontFamily: 'Roboto',
                    fontWeight: 'normal'

                },
                marker: {
                    size: 14,
                    shape: 'square'
                },
                line: {
                    strokeWidth: 12
                }
            }

        }
    };

    const graph1 = [
        'This graph highlights the buffer trend of MTA Raw Materials (stock buffer).'
    ]

    const handleSubmitClick = () => {
        setNumericData(filterDataByDaysGap(data, 0, horizonDays, (actBtn.label === 'Percentage')));
    }

    const updateGraphState = async () => {
        if (actBtn.label === 'Percentage') {

            setActBtn({
                label: "Absolute Value",
                value: 'Absolute Value'
            })
            setNumericData(data);
            setNumericData(filterDataByDaysGap(numericData, 0, horizonDays, true));
            setNumericData(filterDataByDaysGap(data, 0, horizonDays, (actBtn.label !== 'Percentage')));
        }
        else {
            setActBtn({
                label: "Percentage",
                value: 'Percentage'
            })
            setNumericData(convertToPercentage(data))
            setNumericData(filterDataByDaysGap(numericData, 0, horizonDays, false));
            setNumericData(filterDataByDaysGap(data, 0, horizonDays, (actBtn.label !== 'Percentage')));

        }

    }
    const [hideChart1, toggleChart1] = useState(false);

    const colDef =
        [
            {
                field: 'dt',
                colId: 'dt',
                headerName: 'Date',
                initialWidth: 200
            },
            {
                field: 'b',
                colId: 'b',
                headerName: 'Black',
                initialWidth: 200

            },
            {
                field: 'r',
                colId: 'r',
                headerName: 'Red',
                initialWidth: 200

            }
            ,
            {
                field: 'g',
                colId: 'g',
                headerName: 'Green',
                initialWidth: 200

            }
            ,
            {
                field: 'y',
                colId: 'y',
                headerName: 'Yellow',
                initialWidth: 200

            }
            ,
            {
                field: 'w',
                colId: 'w',
                headerName: 'White',
                initialWidth: 200

            }
        ]



    const generateHeader = () => {
        return (
            
                <SCChartMainContainer style={{ zoom: 1, width: '100%' }}>
                    <SCChartSliderContainer style={{ zoom: 0.75, marginTop: '6px' }}>
                        <label style={{
                            fontStyle: "normal",
                            fontVariant: "normal",
                            fontWeight: 400,
                            fontSize: 15,
                            fontFamily: "Roboto",
                            paddingLeft: '10px'
                        }}
                        > <b>Select Horizon (in days):  </b></label>
                        <VFRangeSlider
                            showTriangle={false}
                            min={1}
                            max={90}
                            milestones={[0, 30, 60, 90]}
                            strictMode={false}
                            width={200}
                            defaultValue={horizonDays}
                            handleChange={(e) => setHorizondays(e)}
                            labelValueFormatter={(value: number) => value.toString()}
                        />
                        <VFButton
                            onClick={() => handleSubmitClick()}
                            themeUi={themeUi}
                            disabled={false}
                            style={{
                                height: "35px",
                                width: "50px",
                                borderRadius: "3px",
                            }}
                        >   
                            <img
                                src="/assets/img/rightArrowHorizontal.svg"
                                height={13}
                                width={7}
                            />
                        </VFButton>
                        
                    </SCChartSliderContainer>
                    <SCChartHeaderContainer style={{ background: 'transparent' }}>

                        <CapsuleWrapper style={{ zoom: 0.8, padding: '4px' }}>
                            <VFCapsule
                                activeBtn={actBtn}
                                capsules={[

                                    {
                                        label: "Percentage",
                                        value: 'Percentage'
                                    },
                                    {
                                        label: "Absolute Value",
                                        value: 'Absolute Value'
                                    }
                                ]}
                                handleClick={() => updateGraphState()}


                            />
                        </CapsuleWrapper>
                        <div style={{ marginLeft: 30, marginBottom: '-5px' }}>
                            <VFInfoToolTip infoList={graph1} />
                        </div>
                        <div onClick={() => { toggleChart1(!hideChart1) }} style={{ marginLeft: 10, marginBottom: '-5px', marginRight: '10px' }}>
                            <img src='/assets/img/VectorFLOW/BPR/minimize.svg' height={13} width={13} color={"#CCCCCC"} />
                        </div>
                    </SCChartHeaderContainer>
                </SCChartMainContainer>
            

        )
    }


    const graphTitleJSX = <div
        data-testid="ot-if-graph"
        style={{
            fontSize: "13px",
            margin: "0 auto",

            textAlign: "center",
        }}
    >
        <span style={{ fontWeight: 500 }}>RM / PM On Hand Invetory Trend - MTA </span>
        <span style={{ fontWeight: 300 }}>{`  (${moment(lastRunDate).subtract(horizonDays - 1, 'days').format('D MMM YYYY')} - ${moment(lastRunDate).format('D MMM YYYY')})`}</span>
    </div>

    return (
        <div style={{ height: "100%", display: 'flex', justifyContent: 'left', marginLeft: '12px', paddingBottom: '5px' }}>


            <SplitGraphContainer
                tableLoading={tableLoading}
                chartLoading={chartLoading}
                setTableLoading={setTableLoading}
                setChartLoading={setChartLoading}
                data={numericData}
                rowData={numericData}
                graphTitle={''}
                graphTitleJSX={graphTitleJSX}
                tableTitle={`RM / PM On Hand Invetory Trend - MTA (${moment(lastRunDate).subtract(horizonDays - 1, 'days').format('D MMM YYYY')} - ${moment(lastRunDate).format('D MMM YYYY')})`}
                options={options}
                colDef={colDef}
                header={generateHeader}
                hideChart={hideChart1}
                toggleChart={toggleChart1}
                TooltipRenderer={TooltipRenderer}
                graphType={1}
            />
        </div>
    )
}

export default BTMTA