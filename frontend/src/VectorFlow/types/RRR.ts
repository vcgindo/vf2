export interface RRRField {
    Report_Name:string
    Col_Code:string
    Col_Position:number
    Header:string
    Visible:boolean
    CellAlignment:string
    Value:string
    DataType:"String" | "Number" | "Boolean"
}

export interface RRRDataPayload{
    filters:any
    paginationParameter:{
        pageNumber:number,
        recordsPerPage:number
    }
}

