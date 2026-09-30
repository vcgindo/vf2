export interface ColumnHeaderConfig {
    jf: string
    cp: number
    hdr: string
    vs: boolean
    ca: string
    val: string
}

export interface ColumnHeaderConfigDataPayload {
    filters: any[]
    paginationParameter: {
        pageNumber: number,
        recordsPerPage: number
    }
}


