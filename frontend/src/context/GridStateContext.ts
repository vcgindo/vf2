import{createContext} from 'react'

interface GridStateContextProps{
    ref:any
    exportExcelColumns:Array<any>
    setExportExcelColumns:any
    tempDownloadData:boolean
    setTempDownloadData:any
    exportExcelRowData:Array<any>
    setExportExcelRowData:any,
    onResetCallback?:any,
    gridColDefs?:any,
    globalColDef?:any,
    setGlobalColDef?: any
}

export const GridStateContext = createContext<GridStateContextProps>({
    ref:null,
    gridColDefs:[],
    globalColDef:[],
    setGlobalColDef:()=>{return},
    exportExcelColumns:[],
    setExportExcelColumns:()=>{return},
    tempDownloadData:false,
    setTempDownloadData:()=>{return},
    exportExcelRowData:[],
    setExportExcelRowData:()=>{return},
    onResetCallback:()=>{return}
})

