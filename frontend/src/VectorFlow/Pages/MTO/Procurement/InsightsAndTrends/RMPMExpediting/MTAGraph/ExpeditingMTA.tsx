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
import { notifyError } from './../../../../../../../helpers/notify'
import OverlayLoader from '../../../../../../../VectorFlow/Pages/MTO/Common/Loader'


interface SupplierData {
    [key: string]: {
        [key: string]: number;
    };
}
interface Product {
    rn: string;  // Product ID
    c: number;   // Value for the product ID
}

interface Result {
    sn: string;
    rc: number;
    tt: Product[];  // Array of product objects with rn and c
}

const ExpeditingMTA = (props: { isMTO: boolean, date: string, supplierHorizon: any, setSupplierHorizon: (days: any) => void, getFilterData: () => void, appliedFilters: any  }) => {
    const { date, supplierHorizon, setSupplierHorizon, getFilterData, appliedFilters } = props;
    let RMPMExpeditionOBj = {}
    const [chartLoading, setChartLoading] = useState(false);
    const [tableLoading, setTableLoading] = useState(false);

    const { mutateAsync: getRMPMExpedition, isLoading: loading } = useGetRMExpeditingData()
    const [numericData, setNumericData] = useState<any>();

    useEffect(() => {
        if(Object.keys(appliedFilters).length){

            getRMHorizonBasedData();
        }
    }, [appliedFilters])


    const transformSupplierData = (data: SupplierData): Result[] => {
        // Initialize an empty array to store the result
        const result: Result[] = [];
        // Loop through each supplier in the data
        for (const supplier in data) {
            // Calculate the sum of values for each supplier
            const total = Object.values(data[supplier]).reduce((acc, value) => acc + value, 0);
            // Push the result in the desired format

            // Create the tt array, which contains objects with rn and c for each product
            const tt = Object.entries(data[supplier]).map(([productId, value]) => ({
                rn: productId,
                c: value,
            }));

            // Push the result in the desired format
            result.push({
                sn: supplier,
                rc: total,
                tt: tt,  // Add array of product details
            });
        }
        // Sort the result array in descending order based on 'rn'
        result.sort((a, b) => b.rc - a.rc);

        return result;
    };

    const TooltipRenderer = ({ datum }: any) => {

        return `
        <div style="background:#000; border-radius:3px; color:#fff; padding:8px">
            ${datum.tt.map((item: { rn: string; c: number }) => `
                <div style="width: 100%; display: flex; justify-content: space-between; padding: 5px 0;">
                    <div style="text-align: left;">${item.rn} :</div>
                    <div style="text-align: right;">${item.c}</div>
                </div>
            `).join('')}
            <hr style="border: 1px dashed"/>
            <div>No. Of Orders : ${datum.rc}</div>
        </div>
    `;
    }




    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;


    const options: AgChartOptions = {
        axes: [
            {
                title: { text: 'Supplier Name', fontSize: 10, spacing: 20 },
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
        series: [
            {
                type: 'bar',
                xKey: "sn",
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
        'The graph highlights the suppliers based on their impact on timely release of orders'
    ]
    const getRMHorizonBasedData = async () => {
        //setNumericData(null)
        try {
            RMPMExpeditionOBj = {
                'horizon': supplierHorizon,
                'val': 'supplier'
            }
            const formatedFilters = formatFilterJSON(appliedFilters);
            const someData = await getRMPMExpedition({...RMPMExpeditionOBj, appliedFilters: formatedFilters});
            const xAxisValue = transformSupplierData(someData?.data?.data?.supplier);
            setNumericData(xAxisValue)
        } catch (error) {
            console.error("Error fetching RM Horizon based data:", error);
            notifyError("Failed to fetch RM Horizon based data. Please try again later.");
        }
    }

    const handleSubmitClick = () => {
        //setNumericData();
        // getFilterData();
        getRMHorizonBasedData();
    }

    const handleSliderChange = (val: any) => {
        setSupplierHorizon(val)
    }


    const [hideChart1, toggleChart1] = useState(false);

    const colDef =
        [
            {
                field: 'sn',
                colId: 'sn',
                headerName: 'Suplier Name',
                initialWidth: 200
            },
            {
                field: 'rc',
                colId: 'rc',
                headerName: 'Impacted Order',
                initialWidth: 200

            },

        ]
    // const [rowData, setRowData] = useState(data)
    const rowData = numericData;


    const generateHeader = () => {
        return (
            <>
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
                            defaultValue={supplierHorizon}
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
                        <div onClick={() => { toggleChart1(!hideChart1) }} style={{ marginLeft: 10, marginBottom: '-5px', marginRight: '10px' }}>
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
        <span style={{ fontWeight: 500 }}>Top 10 Suppliers Impacting Orders With Release Date In Selected Horizon </span>
        <span style={{ fontWeight: 300 }}>{` ( ${moment(date).format('D MMM YYYY')} - ${moment(date).add(supplierHorizon, 'days').format('D MMM YYYY')})`}</span>
    </div>

    return (
        <div style={{ height: "100%", display: 'flex', justifyContent: 'left', marginLeft: '12px', paddingBottom: '5px' }}>


            {loading && <OverlayLoader/>}
            <SplitGraphContainer
                tableLoading={tableLoading}
                chartLoading={chartLoading}
                setTableLoading={setTableLoading}
                setChartLoading={setChartLoading}
                data={numericData}
                rowData={rowData}
                graphTitle={''}
                graphTitleJSX={graphTitleJSX}
                tableTitle={`Top 10 Suppliers Impacting Orders With Release Date In Selected Horizon ( ${moment(date).format('D MMM YYYY')} - ${moment(date).add(supplierHorizon, 'days').format('D MMM YYYY')})`}
                options={options}
                colDef={colDef}
                header={generateHeader}
                hideChart={hideChart1}
                toggleChart={toggleChart1}
                TooltipRenderer={TooltipRenderer}
                graphType={3}
            />
        </div>
    )
}

export default React.memo(ExpeditingMTA)