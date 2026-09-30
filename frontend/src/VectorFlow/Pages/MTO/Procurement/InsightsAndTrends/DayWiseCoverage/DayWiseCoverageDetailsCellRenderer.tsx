import React from 'react'
import { GridOptions } from 'ag-grid-enterprise'
import VFTable from "../../../Common/VFTable";
import { SCDynamicContainer } from '../../MaterialCoverage/styles';

const DayWiseCoverageDetailsCellRenderer = (params: any) => {

    const options: GridOptions<any> = {
        sideBar: false,
        columnDefs: [
            {
                headerName: "Missing RM Qty", field: "mrq",
                cellStyle: {
                    justifyContent: "center",
                    alignItems: "center",
                    display: "flex",

                },
                cellRenderer: (params: any) => {
                    return (<div style={{ borderRadius: "50%", background: params.data.rmq == params.data.rmal ? "#33800B" : "#E53F3F", width: "30px", height: "30px", display: "flex", justifyContent: "center", alignItems: "center", padding: "1.5rem", color: "white" }}>
                        {params.value}
                    </div>)
                }
            },
            { headerName: "RM Code", field: "rmc" },
            { headerName: "RM Descp", field: "rmd" },
            { headerName: "RM ReqQty", field: "rmq" },
            { headerName: "RM Available", field: "rmav" },
            { headerName: "RM Allocated", field: "rmal" },
        ],
        defaultColDef: {
            suppressMenu: true,
            cellStyle: {
                textAlign: "center"
            }
            // flex: 1
        },
    }


    return (
        // <div>{params.data.status}</div>
        <div style={{padding: "1rem"}}>
            <h4 style={{ margin: "0px",padding: "0.25rem 0rem 1rem 2rem" ,fontSize: '1.2rem'}}>Raw Material Details</h4>
            <SCDynamicContainer>
                <VFTable
                    className='child-grid'
                    pagination={true}
                    gridOptions={options}
                    rowData={params.data?.children}
                    height={"470px"}
                    onGridReady={(params: any) => {
                        params?.api?.autoSizeAllColumns()
                    }}
                />
            </SCDynamicContainer>        
        </div>
    )
}

export default DayWiseCoverageDetailsCellRenderer