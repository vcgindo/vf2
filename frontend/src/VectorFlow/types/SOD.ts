export interface ODFields {
    jf: string
    cp: number
    hdr: string
    vs: boolean
    ca: string
    val: string
}
 
export interface ODDataPayload {
    filters: any[]
    paginationParameter: {
        pageNumber: number,
        recordsPerPage: number
    }
}