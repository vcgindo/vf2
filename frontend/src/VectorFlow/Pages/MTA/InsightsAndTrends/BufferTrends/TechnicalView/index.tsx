
import "allotment/dist/style.css";
import { CapsuleWrapper, ChartWrapper } from "./styles";
import {
    SCChartHeaderContainer, SCChartContainer, SCHorizontalDivider
    , SCChartSliderContainer, SCChartMainContainer
} from '../styles';
import { BufferTrendsGraphState } from '../../../../../types/BPR'
import VFCapsule from "../../../../../../components/VectorFLOW/commons/VFCapsule";
import VFRangeSlider from "../../../../../../components/VectorFLOW/commons/VFRangeSlider";


import { AgCharts } from "ag-charts-react";
import { AgChartOptions } from "ag-charts-community";
import VFInfoToolTip from ".././../../../../../components/VectorFLOW/commons/VFInfoToolTip";


interface TechnicalWiseProps {
    data: any
    currentPageTab: string
    handleClick?: (value: any, index: any) => void
    isLoading: boolean
    graphs: BufferTrendsGraphState[]
    updateGraphState: (id: number, property: string, value: any) => void
    setHorizondays: any
    handleSubmitClick: () => void
    horizonDays: number
    themeUi:string
}


const TechnicalWise = ({ data, isLoading, graphs, updateGraphState, setHorizondays, handleSubmitClick, horizonDays,themeUi }: TechnicalWiseProps) => {


    const numericData = data?.map((item: any) => ({
        ...item,
        b: parseFloat(item.b),
        bu: parseFloat(item.bu),
        y: parseFloat(item.y),
        g: parseFloat(item.g),
        w: parseFloat(item.w),
        r:parseFloat(item.r),
        total:parseFloat(item.total)
        // Parse the string to a floating-point number
    }));


    const colors = [
        { label: 'Black', value: 'black' },
        { label: 'Red', value: 'Red' },
        { label: 'Yellow', value: '#FFBF00' },
        { label: 'Green', value: 'Green' },
        { label: 'Blue', value: 'Blue' },
        { label: 'White', value: 'grey' },
    ];
    
    function TooltipRenderer({ datum }: any) {
    
        return `
            <div style="background:#6C696A; color:white; padding:10px;">
                <div style="color: white; padding: 5px; text-align: center;">
                    <b>${datum.dt || "No Date"}</b>
                </div>
                <table style="width: 100%; color: white; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style=" text-align: left;">Category</th>
                            <th style=" text-align: right;">
                                ${graphs[0].pen.label === 'Percentage' ? 'Percentage' : 'Count'}
                            </th>
                        </tr>
                    </thead>
                    <tbody styles="text-align:left;">
                        ${colors.map(color => {
                            const key = color.value === 'black' ? 'b' :
                                        color.value === 'Red' ? 'r' :
                                        color.value === '#FFBF00' ? 'y' :
                                        color.value === 'Green' ? 'g' :
                                        color.value === 'Blue' ? 'bu' : 
                                        color.value === 'grey' ? 'w' : null;
    
                            if (!key) return ''; 
    
                            return `
                                <tr>
                                    <td style="padding: 5px; background-color: #6C696A;">
                                        <div style="display: flex; align-items: center;">
                                            <div style="margin-right: 10px; height: 10px; width: 15px; background-color: ${color.value} ;"></div>
                                            ${color.label}
                                        </div>
                                    </td>
                                    <td style="padding: 5px; background-color: #6C696A; text-align: right;">
                                            ${graphs[0].pen.label === 'Percentage' 
                                            ? (() => {
                                                const value = parseFloat(datum[key]);
                                                const total = parseFloat(datum.total);
                                                return !isNaN(value) && !isNaN(total) && total > 0
                                                ? Math.round((value / total) * 100) + '%'
                                                : '0%';
                                            })()
                                            : (() => {
                                                const val = parseFloat(datum[key]);
                                                if (isNaN(val)) return '0';
                                                return Number.isInteger(val) ? val : val.toFixed(2);
                                            })()
                                            }
                                        
                                    </td>
                                </tr>
                            `;
                        }).join('')}

                        ${graphs[0].pen.label !== 'Percentage' ? 
                            `
                                <tr>
                                    <td style="padding: 5px; background-color:  #6C696A; font-weight: bold;">
                                        <div style="display: flex; align-items: center;">
                                            Total
                                        </div>
                                    </td>
                                    <td style="padding: 5px; text-align: right; font-weight: bold;">
                                        ${(datum.total).toFixed(2)}
                                    </td>
                                </tr>
                            `
                            : 
                            ''

                        }
                    </tbody>
                </table>
            </div>
        `;
    }

    const options: AgChartOptions = {
        tooltip: {
            position: {
            xOffset: -50,
            yOffset: -10,
        },
        range: "nearest",
    },
        axes: [
            {

                type: "category",
                position: 'bottom',
                label: {
                    fontSize: 8,
                    fontWeight: 'bold',
                    color: 'black',
                    autoRotate:false,
                    avoidCollisions:true
                }
            },
            {
                type: "number",
                position: 'left',
                label: {
                    fontSize: 8,
                    fontWeight: 'bold',
                    color: 'black'
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
                marker: {
                    fill: "Black",
                    stroke: "Black"
                },
                tooltip: {
                    renderer: TooltipRenderer
                },
            },
            {
                type: "line",
                xKey: "dt",
                xName: "Date",
                yKey: "bu",
                yName: "Blue",
                stroke: "Blue",
                marker: {
                    fill: "Blue",
                    stroke: "Blue"
                },
                tooltip: {
                    renderer: TooltipRenderer
                },
            },
            {
                type: "line",
                xKey: "dt",
                xName: "Date",
                yKey: "r",
                yName: "Red",
                stroke: "Red",
                marker: {
                    fill: "Red",
                    stroke: "Red"
                },
                tooltip: {
                    renderer: TooltipRenderer
                },
            },
            {
                type: "line",
                xKey: "dt",
                xName: "Date",
                yKey: "y",
                yName: "Yellow",
                stroke: "Yellow",
                marker: {
                    fill: "#FFBF00",
                    stroke: "#FFBF00"
                },
                tooltip: {
                    renderer: TooltipRenderer
                },
            },
            {
                type: "line",
                xKey: "dt",
                xName: "Date",
                yKey: "g",
                yName: "Green",
                stroke: "Green",
                marker: {
                    fill: "Green",
                    stroke: "Green"
                },
                tooltip: {
                    renderer: TooltipRenderer
                },
            }
            ,
            {
                type: "line",
                xKey: "dt",
                xName: "Date",
                yKey: "w",
                yName: "White",
                stroke: "Grey",
                marker: {
                    fill: "grey",
                    stroke: "grey",

                },
                tooltip: {
                    renderer: TooltipRenderer
                },
            },
            {
                type: "line",
                xKey: "dt",
                xName: "Date",
                yKey: "total",
                yName: "Total",
                stroke: "purple",
                marker: {
                    fill: "purple",
                    stroke: "purple",

                },
                tooltip: {
                    renderer: TooltipRenderer
                },
            strokeWidth: 4
            }

        ],
        legend: {
            position: 'bottom',
            item: {
                label: {
                        formatter:(params:any)=>{
                            if(params.value.length > 10) return params.value.toString().slice(0,10) + '...';
                            return params.value;
                        },
                    fontSize: 12,

                },
                marker: {
                    size: 12,
                    shape:'square'
                },
                line: {
                    strokeWidth: 1
                }
            }

        }
    };

    const graph1 = [
        'This graph shows the trend of number of SKU Locations in Black, Red, Green, Yellow, and White.'
    ]


    return (
        <>
            <SCChartContainer >
                <SCChartMainContainer>
                    <SCChartSliderContainer>
                        <label style={{
                            fontStyle: "normal",
                            fontVariant: "normal",
                            fontWeight: 400,
                            fontSize: 15,
                            fontFamily: "Roboto",
                            paddingLeft: '10px'
                        }}
                        > <b>Select Horizon: </b></label>
                        <VFRangeSlider
                            showTriangle={false}
                            min={1}
                            max={90}
                            milestones={[0, 1, 90]}
                            strictMode={false}
                            width={250}
                            defaultValue={horizonDays}
                            handleChange={(e) => setHorizondays(e)}
                            labelValueFormatter={(value: number) => value > 1 ? `${value} Days` : `${value} Day`}
                        />
                        <div style={{ zoom: 0.8 }}>
                            {/* <VFButtonOutline themeUi={user.user.theme_ui} onClick={handleSubmitClick} width={120} disabled={false} style={{fontSize:'15px',height:'42px',fontWeight:500}}>
                                        Submit
                                    </VFButtonOutline> */}
                            <img
                                style={{ cursor: 'pointer' }}
                                src={themeUi==="REGALBLAZE"?"/assets/img/Group 627-regal.svg":"/assets/img/Group 627.svg"}
                                height={50}
                                width={60}
                                onClick={() => handleSubmitClick()}
                            />
                        </div>


                    </SCChartSliderContainer>
                    <SCChartHeaderContainer>
                        <CapsuleWrapper>
                            <VFCapsule
                                activeBtn={graphs[0].pen}
                                capsules={[

                                    {
                                        label: "Percentage",
                                        value: 'Percentage'
                                    },
                                    {
                                        label: "Absolute Value",
                                        value: 'Absolute'
                                    }
                                ]}
                                handleClick={(value: any) => updateGraphState(1, "pen", value)}

                            />
                        </CapsuleWrapper>
                    </SCChartHeaderContainer>
                </SCChartMainContainer>

                <SCHorizontalDivider />
                <ChartWrapper>
                    <div style={{ height: '100%', width: '100%' }}>
                        <div className="title" style={{ backgroundColor: 'white', height: '40px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                            <div style={{ fontSize: '14px', fontWeight: 500, textAlign: 'center' }}>
                                Buffer Trend Graph
                            </div>
                            <div style={{ marginLeft: 10,marginBottom:'-5px' }}>
                                <VFInfoToolTip infoList={graph1} />
                            </div>
                        </div>
                        <AgCharts options={{ ...options, data: numericData }} />
                    </div>
                </ChartWrapper>
            </SCChartContainer>
            {!isLoading && (<div style={{ marginLeft: '10px', marginRight: '10px' }}>
                {/* <VFInfoTip text={graph1}/> */}
            </div>)}
        </>
    )

}

export default TechnicalWise;