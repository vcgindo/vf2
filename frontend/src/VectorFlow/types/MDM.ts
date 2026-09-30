import {
    GridApi,
    ColDef
} from 'ag-grid-enterprise'
import Joi from 'joi'

export type ViewModifyProgressState = "default" | "view" | "error" | "uploaded" | "submitted" | "savedToDraft" | "editOnline"  | "editOnlineSubmitted" | "seasonality" | "phaseInPhaseOut" | "deleteUploaded" | "deleteView"| "deleteOnline"  | "deleteOnlineSubmitted" | 'Discard' | "DiscardDraft" | "conflicts" | "editOnlineConflicts" | "mtoView";
export interface MDMStore{
    allMasters:MDMMasterState[],
    masters:MDMMasterState[],
    options:Option[],
    selectedOptions:Option[],
    activeMaster:MDMMasterState,
    isSelectMasterOpen:boolean,
    draftId:string
    isUploadModalOpen:boolean,
    chunkSize:number,
    recordCount:number,
    isDataAvailableLocally:boolean
    lastRunDate:string,
    isSavingToDraft?:boolean
}

export interface MDMMasterState {
    id: number,
    name: string,
    colDefs: ColDef[]
    rowData: any[]
    filters: Filter[]
    progress: ViewModifyProgressState,
    fields: Field[],
    isChecked: boolean,
    isMTO?: boolean
}
export interface Master {
    id: number,
    name: string,
    fields: Field[]
    isMTO?: boolean
}

export interface Option {
    label: string,
    value: string
}

export interface Field {
    displayName: string,
    key: string,
    visible: boolean
    isEdit: boolean
    isAdd: boolean
    isDownload: boolean
    isDelete?: boolean
    col_Position: string
    isApplicable: boolean
    dataType: string
}

export interface Tab {
    id: number,
    fields: Field[],
    name: string,
    status: string
}

export interface Filter {
    id: string
    masterId: number | undefined,
    field: string
    operator: string
    text: string
}

export interface GetMasterDataPayload {
    id: number,
    name: string,
    filters: Array<{ attributeName: string, op: string, value: string }>,
    fields: Array<{ key: string }>,
    paginationParameter?: PaginationPayload | object

}

export interface PaginationPayload {
    pageNumber: number,
    recordsPerPage: number
}

export interface VFtableProps {
    rowData: Array<any>
    columnDefs: ColDef[] | undefined
    ref: any
    onColumnChange: () => void
}

export interface GridRef {
    api: GridApi
    columnApi: any
}

export interface AddRecordMaster {
    id: number,
    name: string
}

export interface AddRecordMasterGroup {
    name: string
    masters: AddRecordMaster[]
}
export interface MasterIdToSchema {
    [key: string]: Joi.ObjectSchema<any>
}


export interface QueryFilteredDataConfigs {
    filters: Array<{ attributeName: string, op: string, value: string }>,
    fields: Array<{ key: string }>
    showAll?: boolean,
    pagination?: boolean
    count?: boolean,
    currentPage?: number
    rowsPerPage?: number
}

export interface UploadModalRadioButtonsType {
    label: string
    value: any
}
export interface NormHistory {
    date: string,
    old_norm: string,
    new_norm: string,
    change_reason: string
}

export interface DailyData {
    date: string,
    stock: string,
    git: string
}
export interface SeasonalityQuickFilterType {
    id: number[]
    label: string
    color: string
}

export interface DraftActionType {
    id: number
    label: string
    value: string
}

export interface ConflictToolTipUser {
    name: string
    column: string
    value: string
}
export interface TaskDataType {
    Actiontype: number,
    PendingSince: string,
    RequesterName: string,
    SrNo: number,
    TaskID: string,
    TaskName: string,
    ageing: number
}

// export interface DataModificationHistory {


// }
