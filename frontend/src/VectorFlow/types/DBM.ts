export interface DBMField {
    Report_Name:string
    Col_Code:string
    Col_Position:number
    Header:string
    Visible:boolean
    CellAlignment:string
    Value:string
    DataType:"Number" | "String" | "Boolean"
}

export interface DBMDataPayload{
    filters:any[]
    paginationParameter:{
        pageNumber:number,
        recordsPerPage:number
    }
}