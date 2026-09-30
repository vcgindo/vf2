import { AgChartOptions } from 'ag-charts-community'
import React, { useEffect, useState } from 'react'
import VFInfoToolTip from '../../../../../../../components/VectorFLOW/commons/VFInfoToolTip'
import VFRangeSlider from '../../../../../../../VectorFlow/Pages/MTO/Common/VFRangeSlider'
import { SCChartHeaderContainer, SCChartMainContainer, SCChartSliderContainer } from '../../styles'

import SplitGraphContainer from '../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer';
import { useGetRMExpeditingData } from '../../../../../../Services/MTO/Production/InsightsAndTrends/RMPMExpediting/index';
import moment from 'moment'
import { formatFilterJSON } from '../../../../../../../helpers/utils'
import { useUserData } from '../../../../../../../../src/context'
import VFButton from '../../../../../../../components/VectorFLOW/commons/VFButton'
import { notifyError } from '../../../../../../../helpers/notify'
import OverlayLoader from '../../../../../../../VectorFlow/Pages/MTO/Common/Loader'

const ExpeditingMTO = (props: { isMTO: boolean, date: string, rmHorizon: any, setRmHorizon: (day: any) => void, getFilterData: () => void, appliedFilters: any }) => {
    const { date, rmHorizon, setRmHorizon, getFilterData, appliedFilters } = props;
    const { mutateAsync: getRMPMExpedition , isLoading: loading} = useGetRMExpeditingData()
    const [numericData, setNumericData] = useState<any>();
    
    let RMPMExpeditionOBj = {}
    useEffect(() => {
        if(Object.keys(appliedFilters).length){

            getRMHorizonBasedData();
        }
    }, [appliedFilters])

    function TooltipRenderer({ datum }: any) {
        return ` 
        <div style="background:#000; border-radius:3px; color:#fff ;padding:8px">
            <div style="width: 100%; display: flex; justify-content: center">
              ${datum.rn}
            </div>
            <hr style="border: 1px dashed"/>
            <div>RM Desc : ${datum.rd}</div>
            <div>No. Of Orders : ${datum.rc}</div>
        </div>
        `;
    }

    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;


    const options: AgChartOptions = {
        //Porperties to set here for x and y axises
        axes: [
            {
                title: { text: 'Raw Material', fontSize: 10, spacing: 20 },
                type: "category",
                position: 'bottom',
                label: {
                    fontSize: 8,
                    fontWeight: 'bold',
                    color: 'black'
                },
                gridLine: {
                    enabled: false
                }
            },
            {
                title: { text: "No. Of Impacted Orders", fontSize: 10, spacing: 3 },
                type: "number",
                line: { enabled: true },
                position: 'left',
                label: {
                    formatter: function (params) {
                        return (params.value);
                    },
                    fontSize: 8,
                    fontWeight: 'bold',
                    color: 'black'
                },
                gridLine: {
                    enabled: false
                }
            }
        ],
        //what series you want to show e.g. line, bar, etc with its properties
        series: [
            {
                type: "bar",
                xKey: "rn",
                yKey: "rc",
                fill: 'Grey',
                yName: "No of Impacted Orders",
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
        'This graph highlights the raw materials in shortage, ranked by thier impact on the numbers of orders.'
    ]

    const getRMHorizonBasedData = async () => {
        //setNumericData(null)
        try {
            RMPMExpeditionOBj = {
                'horizon': rmHorizon,
                'val': 'rm'
            }
            const formatedFilters = formatFilterJSON(appliedFilters);
            const someData = await getRMPMExpedition({...RMPMExpeditionOBj, appliedFilters: formatedFilters });
            setNumericData(someData.data?.data?.rm)
        } catch (error) {
            console.log("Error fetching RM expediting data:", error);
            notifyError("Failed to fetch RM expediting data. Please try again later.");
        }
    }

    const handleSubmitClick = () => {
        //setNumericData();
        // getFilterData();
        getRMHorizonBasedData();
    }

    const handleSliderChange = (val: any) => {
        setRmHorizon(val)
    }


    const [hideChart1, toggleChart1] = useState(false);

    const colDef =
        [
            {
                field: 'rn',
                colId: 'rn',
                headerName: 'RM Name',
                initialWidth: 200
            },
            {
                field: 'rc',
                colId: 'rc',
                headerName: 'Order Count',
                initialWidth: 200

            },
            {
                field: 'rd',
                colId: 'rd',
                headerName: 'RM Desc',
                initialWidth: 200

            }

        ]



    const [chartLoading, setChartLoading] = useState(true);
    const [tableLoading, setTableLoading] = useState(true);

    const generateHeader = () => {
        return (
            <>
            {loading && <OverlayLoader />}
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
                        > <b>Select Horizon (in days): </b></label>
                        <VFRangeSlider
                            showTriangle={false}
                            min={1}
                            max={90}
                            milestones={[0, 30, 60, 90]}
                            strictMode={false}
                            width={200}
                            defaultValue={rmHorizon}
                            handleChange={(e) => handleSliderChange(e)}
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

                        <div style={{ marginLeft: 30, marginBottom: '-5px' }}>
                            <VFInfoToolTip infoList={graph1} />
                        </div>
                        <div
                            onClick={() => { toggleChart1(!hideChart1) }} style={{ marginLeft: 10, marginBottom: '-5px', marginRight: '10px' }}>
                            <img src='/assets/img/VectorFLOW/BPR/minimize.svg' height={13} width={13} color={"#CCCCCC"} />
                        </div>
                    </SCChartHeaderContainer>
                </SCChartMainContainer>
            </>

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
        <span style={{ fontWeight: 500 }}>Top 10 Raw Materials Impacting Orders With Release Date In Selected Horizon</span>
        <span style={{ fontWeight: 300 }}>{` (${moment(date).format('D MMM YYYY')} - ${moment(date).add(rmHorizon, 'days').format('D MMM YYYY')}) `}</span>
    </div>


    return (
        <div style={{ height: "100%", display: 'flex', justifyContent: 'left', marginRight: '4px', paddingBottom: "5px" }}>


            <SplitGraphContainer
                tableLoading={tableLoading}
                chartLoading={chartLoading}
                setTableLoading={setTableLoading}
                setChartLoading={setChartLoading}
                data={numericData}
                rowData={numericData}
                graphTitle={''}
                graphTitleJSX={graphTitleJSX}
                tableTitle={`Top 10 Raw Materials Impacting Orders With Release Date In Selected Horizon (${moment(date).format('Do MMMM YYYY')} - ${moment(date).add(rmHorizon, 'days').format('Do MMMM YYYY')})`}
                options={options}
                colDef={colDef}
                header={generateHeader}
                hideChart={hideChart1}
                toggleChart={toggleChart1}
                TooltipRenderer={TooltipRenderer}
                graphType={2}
            />


        </div>

    )
}

export default React.memo(ExpeditingMTO)