export interface BTRCategory {
    bgColor: string;
    color: string;
    cellLabel: string;
    toolTipHeader:string;
    toolTipDescription:string
}

export interface BTRCategoryMapperType {
    [key: string]: BTRCategory;
}