import { CSSProperties } from "react"

export interface BPRField {
    Report_Name:string
    Col_Code:string
    Col_Position:number
    Header:string
    Visible:boolean
    CellAlignment:string
    Value:string
    DataType:"Number" | "String" | "Boolean"
}

export interface BPRDataPayload{
    id: number,
  name: string,
  fields: Array<any>,
    filters:any
    paginationParameter:{
        pageNumber:number,
        recordsPerPage:number
    }
}


export interface BORDataPayload{
    id: number,
  name: string,
  fields: Array<any>,
    filters:any
    paginationParameter:{
        pageNumber:number,
        recordsPerPage:number
    }
}

export interface BPRSubmitRemarkToolTipProps{
    remark:string 
    style:CSSProperties
    setRemark:(params:any)=>void
    onSuccess:()=>void
    onClose:()=>void
    isDate?:boolean
    themeUi:string
}

export interface BPRRemarkHistoryToolTipProps{
    remarkHistory:any[] 
    style:CSSProperties
    onClose:()=>void
}

export interface SubmitBPRRemarkPayload{
    remark:string
    whcode:string
    skucode:string
}

export interface SubmitBORRemarkPayload extends SubmitBPRRemarkPayload{
    spc:string
}

export interface GetDailyDataPayload{
    SKUCode:string,
    WhCode:string
}

export interface BPRFilter{
    type?:string
    name:string
    attributeName:string
    label:string
    operator:string
    value:string
}

export interface BPRFilterGroup{
    id:string
    label:string
    filters:Array<BPRFilter>
}

export interface BPRFilterState{
    supplyChainFilter:BPRFilterGroup
    locationFilter:BPRFilterGroup
    productFilter:BPRFilterGroup
    availabilityFilter:BPRFilterGroup
    coverageFilter:BPRFilterGroup
    colorFilter:BPRFilterGroup
    generalFilter:BPRFilterGroup
    customAttributeFilter:BPRFilterGroup
    horizonFilter:BPRFilterGroup
}

export type AnalyticsDataPayload = Record<string, any>

export type SubmitDueDatePayload = Record<string, any>



export interface ReseachInsightsGraphTypeState{
    label:"Self" | "Child" | "Parent"
    value:"Self" | "Child" | "Parent"
}

export interface ReseachInsightsGraphPenState{
    label:"Eco" | "Tech"
    value:"Eco" | "Tech"
}

export interface ReseachInsightsGraphDateState{
    Red:number
    White:number
    Yellow:number
    Green:number
    Black:number
    Blue:number
    date:string
}


export interface ReseachInsightsGraphDateStateFilter{
    key:string,
    value:string
}

export interface ReseachInsightsGraphState{
    type:ReseachInsightsGraphTypeState
    pen:ReseachInsightsGraphPenState
    id:number
    filters:Array<ReseachInsightsGraphDateStateFilter>
}


export interface BufferTrendsGraphTypeState{
    label:"Self" 
    value:"Self" 
}

export interface BufferTrendsGraphPenState{
    label:"Absolute" | "Percentage"
    value:"Absolute" | "Percentage"
}

export interface BufferTrendsGraphDateState{
    Red:number
    White:number
    Yellow:number
    Green:number
    Black:number
    Blue:number
    date:string
}


export interface BufferTrendsGraphDateStateFilter{
    key:string,
    value:string
}

export interface BufferTrendsGraphState{
    type:BufferTrendsGraphTypeState
    pen:BufferTrendsGraphPenState
    id:number
    filters:Array<BufferTrendsGraphDateStateFilter>
}

export interface NormChangeHistory{
    nCD:string,
    nN:number,
    olN:number,
    rsn:string
}

export interface DailyDataChart{
    cs:number | null,
    dt:string,
    git:number | null,
    rp:number | null,
    stk:number | null,
    rrs:number | null,
    grs:number | null,
    rrc:number | null,
    grc:number | null
}


export interface GridState {
    pivot:boolean
    charts:Array<any>
    columns:Array<any>
}

export type BPRViewTableFilterNumericalOperator = 'equals' | 'doesNotEqual' | 'lessThan' | 'greaterThan'

export type BPRViewTableFilterStringOperator = 'equals' | 'doesNotEqual' | 'contains' | 'doesNotContain'
