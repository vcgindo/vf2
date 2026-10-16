import { useMemo, useRef, useState } from 'react'

import { AgGridReact, AgGridReactProps } from "ag-grid-react"
import { Allotment } from "allotment"

import CustomVFTable from "./CustomVFTable"
import { BTRTableWrapper, BTRTableHeader, LockBtnWrapper, LockBtn, LocktBtnContent, LockLabel, VerticalViewLeftTableWrapper } from "./styles"
import VFPagination from '../../../../../components/VectorFLOW/commons/VFPagination'
// import VFTable from '../../../../../components/VectorFLOW/commons/VFTable'

import './styles.css'
import VFTable from '../../../../../VectorFlow/Pages/MTO/Common/VFTable'


interface SpliViewTableProps extends AgGridReactProps {
    header: string
    paginationProps: any
}

export interface SplitViewProps {
    techTable: SpliViewTableProps
    ecoTable: SpliViewTableProps
    isLocked: boolean
    toggleLockMode: (value: boolean) => void
    themeUi: string,
      initialColumnState?:any
}

const VerticalSplitView = (props: SplitViewProps) => {
    const {
        techTable,
        ecoTable,
        isLocked,
        toggleLockMode,
        themeUi,
        initialColumnState
    } = props

    const ref1 = useRef<AgGridReact>(null)
    const ref2 = useRef<AgGridReact>(null)
    const ref3 = useRef<AgGridReact>(null)


    const [lockBtnPosition, setLockBtnPosition] = useState<number>(0)

    const staticTableColDefs = useMemo<any>(() => {
        if (!techTable.columnDefs) return []
        const colDefs = techTable.columnDefs.filter((col: any) => col.colId && ['dailydatagraph','Category', "LocationName", "Norm", "SKUCode", "SKUDescription", "Tags", "VirtualNorm", "RN", "pc", "pn", "WhCode"].includes(col.colId));
        const newColDef = colDefs.map((source: any) => {
            const colDef = { ...source };
            if (colDef.colId === "Category" || colDef.colId ==="dailydatagraph") {
                colDef.pinned = "left";
                colDef.minWidth =  80;
            } else {
                colDef.pinned = false;
                
            }
            colDef.width = 80;
            colDef.filter=false;
            return colDef;
        });
        return newColDef;
    }, [techTable.columnDefs]);

    const techTableColDefs = useMemo<any>(() => {
        if (!techTable.columnDefs) return []
        const colDefs = techTable.columnDefs.filter((col: any) => col.colId && !['dailydatagraph','Category', "LocationName", "Norm", "SKUCode", "SKUDescription", "Tags", "VirtualNorm", "RN", "pc", "pn","WhCode"].includes(col.colId));
        const newColDef = colDefs.map((source: any) => {
            const colDef = { ...source };
            colDef.pinned = false;
            colDef.filter=false;
            return colDef;
        });
        return newColDef;
    }, [techTable.columnDefs]);

    const ecoTableColDefs = useMemo<any>(() => {
        if (!ecoTable.columnDefs) return []
        const colDefs = ecoTable.columnDefs.filter((col: any) => col.colId && !['dailydatagraph','Category', "LocationName", "Norm", "SKUCode", "SKUDescription", "Tags", "VirtualNorm", "RN", "pc", "pn","WhCode"].includes(col.colId));
        const newColDef = colDefs.map((source: any) => {
            const colDef = { ...source };
            colDef.pinned = false;
            colDef.filter=false;
            return colDef;
        });
        return newColDef
    }, [ecoTable.columnDefs]);

    const handleChange = (sizes: Array<number>) => {
        setLockBtnPosition(sizes[0])
    }

    const isSyncingScrollRef = useRef(false);
    const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);


    const onBodyScroll = (params: any, from: number) => {
        if (
            !isLocked ||
            isSyncingScrollRef.current ||
            (params.direction !== "vertical" && params.direction !== "horizontal")
        ){
            return;
        }

        if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);

        isSyncingScrollRef.current = true;

        const rowHeight = 25;
        const rowCount = techTable.rowData ? techTable.rowData.length : 0;
        const currIndex = Math.min(
            Math.max(Math.round(params.top / rowHeight), 0),
            rowCount - 1
        );

        if (rowCount > 0) {
         
            const syncScroll = () => {
                switch (from) {
                case 1:
                    ref2.current?.api?.ensureIndexVisible(currIndex, "top");
                    ref3.current?.api?.ensureIndexVisible(currIndex, "top");
                    break;
                case 2:
                    ref1.current?.api?.ensureIndexVisible(currIndex, "top");
                    ref3.current?.api?.ensureIndexVisible(currIndex, "top");
                    break;
                case 3:
                    ref1.current?.api?.ensureIndexVisible(currIndex, "top");
                    ref2.current?.api?.ensureIndexVisible(currIndex, "top");
                    break;  
                default:
                    break;
                }
            };
            requestAnimationFrame(syncScroll); 
        }
        scrollTimeoutRef.current = setTimeout(() => {
            isSyncingScrollRef.current = false;
        }, 70);
    };

    const defaultColDef = {
        floatingFilter: false,
        filter: false,
        sortable: false,

    suppressHeaderMenuButton: false,
        // cellStyle: {
        //     "textAlign": "center",
        //     'textOverflow': 'ellipsis',
        //     'whiteSpace': 'nowrap'
        // },
        flex: 1,
        width: 100,
        minWidth: 100,
        cellClass:'btr_cell_style'
    }

    return (
        <BTRTableWrapper>
            <Allotment defaultSizes={[600, 300]} vertical={false} onChange={handleChange}>
                <Allotment.Pane minSize={500}>
                    <BTRTableHeader style={{ display: 'flex', justifyContent: 'flex-start', marginLeft: '50%', height: '35px' }}>{techTable.header}</BTRTableHeader>
                    <VerticalViewLeftTableWrapper>
                        <div style={{ marginTop: -10, height: '95%', width: '100%',minWidth:'50%' }}>
                            <div style={{ height:'100%', display:'flex', flexDirection:'column'}}>
                            <VFTable 
                                key={'ref1'}
                                disableZoomScaling
                                ref={ref1}
                                rowHeight={25}
                                sideBar={null}
                                height={"95%"}
                                gridOptions={{
                                    ...techTable.gridOptions
                                }}
                                statusBar={{
                                        statusPanels:[]
                                }}
                                columnDefs={staticTableColDefs}
                                rowData={techTable.rowData}
                                tooltipMouseTrack={true}
                                tooltipShowDelay={100}
                                // tooltipHideDelay={100000}

                                defaultColDef={defaultColDef}
                                onBodyScroll={(params:any) => onBodyScroll(params, 1)}
                                
                            />
                            </div>
                    {
                    initialColumnState &&
                            <div style={{ zoom: 0.7, margin: '0px -15px'}}>
                                <VFPagination style={{ width:'95%', marginTop:'-30px'}}
                                    {...techTable.paginationProps} isClearGridFilter={false}
                                />
                            </div>
                    }
                        </div>
                        <div style={{ marginTop: -10, height: '95%', width: '100%' ,minWidth:'50%'}}>
                         <div style={{ height:'100%', display:'flex', flexDirection:'column'}}>
                            <VFTable 
                                key={'ref2'}
                                disableZoomScaling
                                ref={ref2}
                                rowHeight={25}
                                sideBar={null}
                                height={"95%"}
                                gridOptions={{
                                    ...techTable.gridOptions
                                }}
                                statusBar={{
                                        statusPanels:[]
                                }}
                                columnDefs={techTableColDefs}
                                rowData={techTable.rowData}
                                tooltipMouseTrack={true}
                                tooltipShowDelay={100}
                                // tooltipHideDelay={100000}
                               
                                defaultColDef={defaultColDef}
                                onBodyScroll={(params:any) => onBodyScroll(params, 2)}
                                alignedGrids={isLocked?[ref3]:[]}
                            />
                            </div>
                {
                    initialColumnState &&
                            <div style={{ zoom: 0.7, margin: '0px -15px'  }}>
                                <VFPagination style={{marginTop:'-30px'}} 
                                    {...techTable.paginationProps} isClearGridFilter={false}
                                />
                            </div>
                }
                        </div>
                    </VerticalViewLeftTableWrapper>
                    {/* <VFTableWrapper>
                        <AgGridReact
                            ref={techRef}
                            gridOptions={{
                                components:techTable.gridOptions?.components
                            }}
                            columnDefs={techTable.columnDefs}
                            rowData={techTable.rowData}
                        />
                    </VFTableWrapper> */}
                </Allotment.Pane>
                <Allotment.Pane minSize={300}>
                    <BTRTableHeader>{ecoTable.header}</BTRTableHeader>
                    <div style={{ marginTop: -10, height: '90%', paddingLeft: '17px' }}>
                         <div style={{ height:'100%', display:'flex', flexDirection:'column'}}>
                            <VFTable 
                                key={'ref3'}
                                disableZoomScaling
                                ref={ref3}
                                rowHeight={25}
                                sideBar={null}
                                height={"95%"}
                                gridOptions={{
                                    ...techTable.gridOptions
                                }}
                                statusBar={{
                                        statusPanels:[]
                                }}
                                columnDefs={ecoTableColDefs}
                                rowData={ecoTable.rowData}
                                tooltipMouseTrack={true}
                                tooltipShowDelay={100}
                                // tooltipHideDelay={100000}
                               
                                defaultColDef={defaultColDef}
                                onBodyScroll={(params:any) => onBodyScroll(params, 3)}
                                alignedGrids={isLocked?[ref2]:[]}
                            />
                            </div>
                    {
                    initialColumnState &&
                        <div style={{ zoom: 0.7, margin: '0px -15px'}}>
                            <VFPagination style={{marginTop:'-30px',paddingRight:'10px'}}
                                {...ecoTable.paginationProps} isClearGridFilter={false}
                            />
                        </div>
                    }
                    </div>
                    {/* <VFTableWrapper>
                        <AgGridReact
                            ref={ecoRef}
                            gridOptions={{
                                components:ecoTable.gridOptions?.components
                            }}
                            columnDefs={ecoTable.columnDefs}
                            rowData={ecoTable.rowData}
                            
                        />
                    </VFTableWrapper> */}
                </Allotment.Pane>
            </Allotment>
            <LockBtnWrapper>
                <LocktBtnContent style={{ left: lockBtnPosition - 37 }}>
                    <LockBtn src={isLocked ? themeUi === "REGALBLAZE" ? "/assets/img/VectorFLOW/BPR/lock-regal.svg" : "/assets/img/VectorFLOW/BPR/lock.svg" : themeUi === "REGALBLAZE" ? "/assets/img/VectorFLOW/BPR/unlock-regal.svg" : "/assets/img/VectorFLOW/BPR/unlock.svg"} onClick={() => toggleLockMode(!isLocked)} />
                    <LockLabel>{isLocked ? "Lock" : "Unlock"}</LockLabel>
                </LocktBtnContent>
            </LockBtnWrapper>

        </BTRTableWrapper>
    )
}

export default VerticalSplitView
