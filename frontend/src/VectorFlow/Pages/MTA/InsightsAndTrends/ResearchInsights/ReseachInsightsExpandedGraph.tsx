import { AgCharts } from "ag-charts-react"
import { AgCartesianChartOptions } from 'ag-charts-community'; 
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { ExpandedChartFilterWrapper, ExpandedChartSelectWrapper, ExpandedChartSelectLabel, ExpandedChartCapsuleWrapper } from "./styles"
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline" 
import Select from 'react-select'
import VFCapsule from "../../../../../components/VectorFLOW/commons/VFCapsule"
import { ReseachInsightsGraphState } from "../../../../../VectorFlow/types/BPR"
import { useUserData } from "../../../../../context"
import { useState } from "react"
import {

    SCViewImage,
    SCViewContainerWithBg,

  } from "../../SupplyChainIntelligenceHub/Planning/ActionToolBar/styles";

interface ExpandedGraphProps {
    id: number
    data: any
    graphs: Array<ReseachInsightsGraphState>
    isOpen: boolean
    onClose: () => void
    options: any
    onTogglePen: (data: any) => void
    onUpdateGraphs: any,
    horizon:any,
    setGraphs: any
}
type ColorKey = "Red" | "Green" | "Yellow" | "Black" | "Blue" | "White";
const colorMap: Record<ColorKey, string> = {
  Red: 'red',
  Green: 'green',
  Yellow: '#FFBF00',
  Black: 'black',
  Blue: 'blue',
  White: 'gray',
};

const ExpandedGraph = (props: ExpandedGraphProps) => {
 
    const {
        data,
        graphs,
        setGraphs,
        id,
        options,
        onClose,
        isOpen,
        onTogglePen,
        onUpdateGraphs,
        horizon
    } = props
 
 
    const activeCapsuleIndex = graphs[id-1].pen
 
    const onChange = (e: any, key: string) => {
        console.log(graphs)
        const doesFilterExist = graphs[id - 1].filters.find((filter) => filter.key === key)
        if (doesFilterExist) {
            return onUpdateGraphs(id, 'filters', graphs[id - 1].filters.map((filter) => filter.key === key ? { key: key, value: e.value } : filter))
        }
        const tempFilters = [...graphs[id - 1].filters, { key: key, value: e.value }]
        onUpdateGraphs(id, 'filters', tempFilters)
    }

    
 
    const handleClose = () => {
        onClose()
        onUpdateGraphs(id, 'filters', [])
    }

    const [selectedLocation, setSelectedLocation] = useState(null);
    const [selectedProduct, setSelectedProduct] = useState(null);
    
    const onreset = (e: any) => {
        onUpdateGraphs(id, "filters", []);
        
        setSelectedLocation(null);
        setSelectedProduct(null);
      };

    const {user} = useUserData();
    const themeUi = user?.user?.theme_ui;

    const yKeys = data && data.length > 0
        ? (Object.keys(data[0]).filter(key => key in colorMap) as ColorKey[])
        : [];

    const createCommonTooltip = (seriesColor: string) => ({
        enabled: true,
        renderer: (params: any) => {
            const { datum, xKey } = params;
            
            const colorRows = yKeys.map(key => {
                const value = datum[key] !== undefined ? datum[key] : 0;
                return `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0;">
                        <span style="color: ${colorMap[key]}; font-weight: 550;">${key}:</span>
                        <span style="margin-left: 12px; font-weight: 550;">${value}</span>
                    </div>
                `;
            }).join('');
            
            return `
                <div style="padding: 0; background: ${seriesColor}; border-radius: 4px; min-width: 100px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
                    <div style="padding: 6px 12px; margin-left: 10px; color: white; font-weight: 550; font-size: 12px;">
                        ${datum[xKey]}
                    </div>
                    <div style="padding: 8px 12px; background: white; border-radius: 0 0 4px 4px; color: #333; font-size: 12px;">
                        ${colorRows}
                    </div>
                </div>
            `;
        },
    });

    const series = yKeys.map(key => ({
        type: "line",
        xKey: "date",
        yKey: key,
        yName: key,
        marker: {
            fill: colorMap[key],
            size: 2,
            shape: 'square',
            stroke: colorMap[key]
        },
        stroke: colorMap[key],
        tooltip: createCommonTooltip(colorMap[key])
    }));

    const chartOptions: AgCartesianChartOptions = {
        height: 400,
        width: 1000,
        data: data,
        series: series as any, 
        axes: [
            {
                type: "category",
                position: 'bottom',
                label: {
                    fontSize: 8
                }
            },
            {
                type: "number",
                position: 'left',
                label: {
                    fontSize: 8
                },
                title: {
                    text: "Count of Item",
                    enabled: true,
                    fontSize: 10,
                    fontFamily: "Roboto",
                }
            }
        ]
    };

    return (
        <VFModalCard

            openModal={isOpen}
            headerIcon=""
            headerBgColor="white"
            headerText={`Technical Trend | Horizon - ${horizon} Days`}
            headerTextColor="black"
            closeIcon='/assets/img/VectorFLOW/NMS/close-dark.svg'
            closeModal={handleClose}

        >
            <ExpandedChartFilterWrapper>
                <ExpandedChartSelectWrapper>
                    <ExpandedChartSelectLabel>Search By Location</ExpandedChartSelectLabel>
                    <Select
                        styles={{
 
                            container: ((baseStyles: any) => ({
                                ...baseStyles,
                                width: 250,
                                // border:'1px solid red',
 
 
                            })),
                            option: (baseStyles, { isSelected }) => ({
                                ...baseStyles,
                                backgroundColor: isSelected ? "#BC3D80" : "white",
 
 
                                "&:hover": {
                                    backgroundColor: '#bc3d814d',
                                    color: "black",
                                }
                            }),
                            control: (baseStyles, { isFocused }) => (
                                {
                                    ...baseStyles,
                                    borderColor: isFocused ? "none" : "hsl(0, 0%, 80%);",
                                    // border: "none",
                                    // borderBottom: error ? "3px solid #D03E3E;" : menuIsOpen || isFocused ? '3px solid #820F4C' : '3px solid #A1A1A1',
                                    boxShadow: 'none',
                                    "&:hover": {
                                        borderColor: isFocused ? "none" : "hsl(0, 0%, 80%);",
 
                                    }
                                }),
                        }}
                        options={options.whcodes}
                        onChange={(e) => {
                            setSelectedLocation(e); 
                            onChange(e, "Whcode");
                          }}
                          value={selectedLocation}
 
                    />
                </ExpandedChartSelectWrapper>
                <ExpandedChartSelectWrapper>
                    <ExpandedChartSelectLabel>Search By Product</ExpandedChartSelectLabel>
                    <Select
                        styles={{
                            container: ((baseStyles: any) => ({
                                ...baseStyles,
                                width: 250
                            })),
                            option: (baseStyles, { isSelected }) => ({
                                ...baseStyles,
                                backgroundColor: isSelected ? "#BC3D80" : "white",
 
 
                                "&:hover": {
                                    backgroundColor: '#bc3d814d',
                                    color: "black",
                                }
                            }),
                            control: (baseStyles, { isFocused }) => (
                                {
                                    ...baseStyles,
                                    borderColor: isFocused ? "none" : "hsl(0, 0%, 80%);",
                                    // border: "none",
                                    // borderBottom: error ? "3px solid #D03E3E;" : menuIsOpen || isFocused ? '3px solid #820F4C' : '3px solid #A1A1A1',
                                    boxShadow: 'none',
                                    "&:hover": {
                                        borderColor: isFocused ? "none" : "hsl(0, 0%, 80%);",
 
                                    }
 
                                }),
                        }}
                        options={options.skus}
                        onChange={(e) => {
                            setSelectedProduct(e); 
                            onChange(e, "SKUCode");
                          }}
                          value={selectedProduct} 
                    />
                </ExpandedChartSelectWrapper>
                {/* <RIButtonOutline themeUi={user.user.theme_ui} onClick={onreset}>
                       Reset Filters
                    </RIButtonOutline> */}
                    <ExpandedChartCapsuleWrapper>
                        
                    <SCViewContainerWithBg
                                          style={{
                                            width:'50px',
                                            height: '50px',
                                            padding: '3px',
                                            // minWidth: '40px',
                                            boxShadow: 'none',   
                                            marginLeft:'-40px',        
                                          }}
                                        onClick={onreset}
                                      >
                                        <SCViewImage
                                          src={
                                            themeUi === "REGALBLAZE"
                                              ? "/assets/img/VectorFLOW/BPR/refresh-regal.svg"
                                              : "/assets/img/VectorFLOW/BPR/refresh.svg"
                                          }
                                          style={{height:'30px'}}
                                          alt=""
                                        />
                                        {/* <p>Reset</p> */}
                                      </SCViewContainerWithBg>
                    </ExpandedChartCapsuleWrapper>


                <ExpandedChartCapsuleWrapper>
                    <VFCapsule
                        activeBtn={activeCapsuleIndex}
                        capsules={[
                            {
                                label: 'On-Hand Inventory',
                                value: 'Tech'
                            },
                            {
                                label: 'Pipeline Inventory',
                                value: 'Eco'
                            }
                        ]}
                        handleClick={onTogglePen}
                    />
                </ExpandedChartCapsuleWrapper>
            </ExpandedChartFilterWrapper>
 
            <AgCharts
                options={chartOptions}
            />
        </VFModalCard>
    )
}
 
export default ExpandedGraph
