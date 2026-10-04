export interface PlanningCounts {
    childMonitorCount:number,
    parentMonitorCount:number,
    childMonitorCustomCount:number,
    parentExpediteCount:number,
    parentExpediteCustomCount:number,
    childExpediteCount:number,
    childExpediteCustomCount:number,
    reviewExcessInventoryCount:number,
    reviewExcessInventoryCustomCount:number,
    reviewOrderFulfillmentCount:number,
    reviewOrderFulfillmentCustomCount:number
}

export interface PlanningCategory {
    category:string,
    childCount?:number,
    parentCount?:number,
    reviewCount?:number,
    custom?:number
}

export interface DailyDataGraph {
    requestId?:string,
    status?:'loading' | 'ready' | 'error',
    runDate?:string,
    normChangeData:any,
    chartData:any,
    masterData:any,
    suggestionData:any,
    monitoringData:any,
    rowData:any

}

export interface MTAStore{
    showDailyDataGraphModal:boolean,
    showNormChangeHistoryTable:boolean
    dailyData:DailyDataGraph
    currentGridState:any
    planning:{
        currentTab:string
        currentCategory:string
        currentView:string
    }
    lastRunDate:string
    EnvConfig:Record<string, any>
    mtaVFMultiFilter:any
}
