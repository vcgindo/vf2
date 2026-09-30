import {BTRCategoryMapperType} from '../VectorFlow/types/BTR'

export const BTRCategoryNumberToTextMapper:any = {
    "1":"SI",
    "2":"CTB",
    "3":"BR",
    "4":"SD",
    "5":"SE",
    "6":"UN",
    "7":"DN"
}

export const BTRCategoryTextToNumberMapper:any =  {
    "SI": "1",
    "CTB": "2",
    "BR": "3",
    "SD": "4",
    "SE": "5",
    "UN": "6",
    "DN": "7"
}

export const BTRCategoryMapper:BTRCategoryMapperType = {
    "CTB":{
        bgColor:"black",
        color:'white',
        cellLabel:"CTB",
        toolTipHeader:"Cont On Hand Black",
        toolTipDescription:"*Total On Hand black days > RLT"
    },
    "SE":{
        bgColor:"#8E8E8E",
        color:'white',
        cellLabel:"SE",
        toolTipHeader:"Stagnated Excess",
        toolTipDescription:"*Consecutive white for 2 RLTs & No consumption in last 2 RLTs"
    },
    "SD":{
        bgColor:" #F02424",
        color:'white',
        cellLabel:"SD",
        toolTipHeader:"Super Delay",
        toolTipDescription:"*>=2*SLt"
    },
    "SI":{
        bgColor:"#355FD3",
        color:'white',
        cellLabel:"SI",
        toolTipHeader:'Supply Chain Issue',
        toolTipDescription:'*Pipeline Black ageing > 1.5 RLTs'
    },
    "BR":{
        bgColor:"linear-gradient(90deg, rgba(41,41,41,1) 50%, rgba(240,36,36,1) 50%)",
        color:'white',
        cellLabel:"B+R",
        toolTipHeader:"Cont On Hand Black+Red",
        toolTipDescription:"*Total On Hand black + red days >=RLT"
    },
    "UN":{
        bgColor:"#D0A928",
        color:'white',
        cellLabel:"UN",
        toolTipHeader:'Upward Norm Revision',
        toolTipDescription:'*any open suggestions for norm increase'
    },
    "DN":{
        bgColor:"#E3812D",
        color:'white',
        cellLabel:"DN",
        toolTipHeader:"Downward Norm Revision",
        toolTipDescription:"*any open suggestions for norm decrease"
    }
}

export const MultiFilterSupplyChainCheckboxList =[
    
    { label: 'Plant', id: '1' },
    { label: 'Supplier', id: '2' },
    { label: 'CWH', id: '3' },
    { label: 'RWH', id: '4' },
    { label: 'Depot', id: '5' },
    { label: 'Distributor', id: '6' },
    { label: 'Retailer', id: '7' }   
]

export const suspensionMessages = [
    { Key: 1, Value: "Suspended as part of exclusions" },
    { Key: 2, Value: "Suspended as Norm is in Sleep Mode" },
    { Key: 4, Value: "Suspended as Phase-In in progress" },
    { Key: 8, Value: "Suspended as Phase-Out in progress" },
    { Key: 16, Value: "Suspended as either norm &lt; Min norm or norm &lt; 2 or RLT,RCP,GCP &lt; 3" },
    { Key: 32, Value: "Suspended as Insufficient Data Points" },
    { Key: 64, Value: "Suspended due to stock is in white" },
    { Key: 128, Value: "Suspended due to Supply Issue" },
    { Key: 256, Value: "Suspended due to New SKU introduction" },
    { Key: 512, Value: "Suspended due to suggestion acceptance" },
    { Key: 1024, Value: "Suspended due to Force Norm Changes" },
    { Key: 2048, Value: "Suspended due to Spike" },
    { Key: 4096, Value: "Suspended due to Suggestion acceptance" },
    { Key: 8192, Value: "Suspended due to Seasonality" }
]

export const GraphSeriesOverrides = {
    column:{
        series:{
            highlightStyle:{
                item:{
                    fill:'rgb(255,255,255,0.2)'
                }
            }
        },
    },
    pie:{
        series:{
            highlightStyle:{
                item:{
                    fill:'rgb(255,255,255,0.2)'
                }
            }
        },
    },
    line:{
        series:{
            highlightStyle:{
                item:{
                    fill:'rgb(255,255,255,0.2)'
                }
            }
        },
    },
    histogram:{
        series:{
            highlightStyle:{
                item:{
                    fill:'rgb(255,255,255,0.2)'
                }
            }
        },
    },
}
export interface RouterToAnalyticsStringMap {
    [route: string]: string;
  }


export const routerToAnalyticsStringMap:RouterToAnalyticsStringMap = {
    // "/supply-chain-intelligence-hub/planning": "planning",
    "/mta/supply-chain-intelligence-hub/bpr": "BPR",
    "/mta/supply-chain-intelligence-hub/rrr": "RRR",
    "/mta/supply-chain-intelligence-hub/bor": "BOR",
    "/mta/dbm/dbm-norm-suggestions": "DBM",
    "/mta/insights-and-trends/research-insights": "RI",
    "/mta/insights-and-trends/buffer-trends":'BTR',
    "/mta/insights-and-trends/buffer-trend-report":'BTR'
  };
  

  export const DBMSuggestionsReasonsToIdMapper:any = {
    "Stockout has occurred today. Upward revision suggested.": "1",
    "Virtual Stockout has occurred. Upward revision suggested.": "2",
    "Stockout has occurred in Red Check Period. Upward revision suggested.": "3",
    "Buffer penetration has consistently been red. Upward revision suggested.": "4",
    "Buffer penetration has consistently been green. Downward revision suggested.": "5",
    "High spike count": "6",
    "Norm 0 Order based Increase": "7",
    "Norm 0 Order based Increase suggestion generated and forcefully accepted": "8",
    "Norm 0 Order based Increase suggestion is not generated but forcefully accepted": "9",
    "Norm 1 Consumption based Increase": "10",
    "Norm 2 Consumption based Decrease": "11"
  }
  

  export const BPRViewTableHeaderFilterStringoptions = [
    {
        value:'contains',
        label:'Contains'
    },
    {
        value:'doesNotContain',
        label:'Does not contain'
    },
    {
        value:'equals',
        label:'Equals'
    },
    {
        value:'doesNotEqual',
        label:'Does not equal'
    }
  ]

  export const BPRViewTableHeaderFilterNumberoptions = [
    {
        value:'equals',
        label:'Equals'
    },
    {
        value:'doesNotEqual',
        label:'Does not equal'
    },
    {
        value:'lessThan',
        label:'Less than'
    },
    {
        value:'greaterThan',
        label:'Greater than '
    }
  ]

  export const defaultAgGridSideBarForBPR = {
    toolPanels: [
      {
        id: "columns",
        labelDefault: "Columns",
        labelKey: "columns",
        iconKey: "columns",
        toolPanel: "agColumnsToolPanel",
        toolPanelParams: {
          suppressPivots: true,
          suppressPivotMode: true,
          suppressRowGroups: true,
          suppressValues: true,
        },
      
      },
    ],
    defaultToolPanel:'',
  }
