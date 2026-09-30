import { ColDef, ColGroupDef } from 'ag-grid-enterprise';
import TaskPendingActionRenderer from '../VectorFlow/Pages/MTA/MDM/TaskPendingForReview/TaskPendingActionRenderer';
import { AbsoluteValueSeasonalitySchema, AddPIPOSchema, AddPOSchema, AddTargetNormSchema, DeltaPercentageSeasonalitySchema, ForceNormChangeSchema, LocationSchema, MOQSchema, SeasonalityStatusSchema, SKULocationSchema, SKUSchema, SOBSchema, StopPIPOSchema } from '../validators/schemas/MTA/MDM/index';
import {type Option, type MasterIdToSchema, SeasonalityQuickFilterType} from '../VectorFlow/types/MDM';
import TaskPendingActionHeader from '../VectorFlow/Pages/MTA/MDM/TaskPendingForReview/TaskPendingActionHeader';
import { SKUSchemaDelete } from '../validators/schemas/MTA/MDM/SKU';
import { LocationSchemaDelete } from '../validators/schemas/MTA/MDM/Location';
import { SKULocationSchemaDelete } from '../validators/schemas/MTA/MDM/SKULocation';
import { SOBSchemaDelete } from '../validators/schemas/MTA/MDM/SOB';

interface masterGroupMapperType {
    masters:string[],
    name:string
}
export const operators:Option[] = [
    {
      label:'Equals To',
      value:'='
    },
    {
        label:'Not Equal To',
        value:'!='
    },
    {
        label:'>',
        value:'>'
    },
    {
        label:'>=',
        value:'>='
    },
    {
        label:'<',
        value:'<'
    },
    {
        label:'<=',
        value:'<='
    },
    {
        label:'Contains',
        value:'contains'
    },
    {
        label:'Starts With',
        value:'startsWith'
    },
    {
        label:'Ends With',
        value:'endsWith'
    },
    {
        label:'Has Value',
        value:'hasValue'
    },
    {
        label:'Has No Value',
        value:'hasNoValue'
    }
  ]

export const operatorDataTypeMapper:any = {
    'String':['=','contains','startsWith','endsWith','hasValue','hasNoValue'],
    'Number':['=','!=','>','>=','<','<=']
}

export const masterIdToSchemaMapper:MasterIdToSchema = {
    '1':SKUSchema,
    '2':LocationSchema,
    '3':SKULocationSchema,
    '4':SOBSchema,
    '5':MOQSchema,
    '6':StopPIPOSchema,
    '7':AddPOSchema,
    '8':AddPIPOSchema,
    '9':AddTargetNormSchema,
    '10':SeasonalityStatusSchema,
    '11':AbsoluteValueSeasonalitySchema,
    '12':DeltaPercentageSeasonalitySchema,
    '13':ForceNormChangeSchema

}

export const masterIdToDeleteSchemaMapper:MasterIdToSchema = {
    '1':SKUSchemaDelete,
    '2':LocationSchemaDelete,
    '3':SKULocationSchemaDelete,
    '4':SOBSchemaDelete
}

export const defaultColDefs:ColDef = {
    minWidth:140,
    cellStyle: {
      "text-align": "center",
      'text-overflow':'ellipsis',
      'white-space':'nowrap'
    },
    flex: 1,
}

export const BTRDefaultColDefs:ColDef = {
    minWidth:80,
    cellStyle: {
      "textAlign": "center",
      'textOverflow':'ellipsis',
      'whiteSpace':'nowrap'
    },
    flex: 1,
    cellClass:'btr_cell_style'
}

export const taskPendingCustomColDefs :any[] = [
    {
        field:'action',
        colId:'action',
        headerName:'Action',
        children:[
            {
                headerComponent:TaskPendingActionHeader,
                cellRenderer:TaskPendingActionRenderer,
                width:300,
                cellStyle:{
                    "border-left":"solid 1px #B9B9B9"
                }
            }
            // {
            //     field:"reject",
            //     colId:'reject',
            //     headerName:"Reject All",
            //     headerCheckboxSelection:true,
            //     cellRenderer:TaskPendingRejectActionButton,
            //     width:150,
            //     cellStyle:{
            //         "border-right":"solid 1px #B9B9B9"
            //     }
            // }
        ],
        cellStyle: {
        "text-align": "center"
        },
        flex: 1,
    },
    {
        field:'status',
        colId:'status',
        headerName:'Status',
        suppressSpanHeaderHeight: true,
        cellStyle:{
            "border-right":"solid 1px #B9B9B9",
            "border-left":"solid 1px #B9B9B9",
            "text-align":'center'
        },
        flex:1,
        minWidth:100
    },
    {
        field:'comments',
        colId:'comments',
        headerName:'Comments',
        suppressSpanHeaderHeight: true,
        editable:true,
        ...defaultColDefs
    }
]

export const taskStatusCustomColDefs :any[] = [
    {
        field:'comments',
        colId:'comments',
        headerName:'Comments',
        cellStyle: {
        "text-align": "center"
        },
        flex: 1,
    },
    {
        field:'status',
        colId:'status',
        headerName:'Status',
        cellStyle:{
            "border-right":"solid 1px #B9B9B9",
            "border-left":"solid 1px #B9B9B9",
            "text-align":'center'
        },
        flex:1,
        minWidth:100
    },
]



export const  seasonalityQuickFilterData:SeasonalityQuickFilterType[] = [
    {
        id:[1],
        label:'Not Started',
        color:'#898989'
    },
    {
        id:[2,3,4,5,6],
        label:'In Progress',
        color:'#EDD44C'
    },
    {
        id:[7],
        label:'Finished',
        color:'#52B736'
    },
    {
        id:[21],
        label:'Aborted',
        color:'#1D1B1C'
    },
    {
        id:[23],
        label:'Stopped',
        color:'#E33A3A'
    }
]
export const masterGroupMapper:masterGroupMapperType[] = [
    {
      name:"SKU",
      masters:['1','27','17','18','25']
    },
    {
      name:"Location",
      masters:['2','15','19','20','21','23','26','22']
    },
    {
      name:"SKU Location",
      masters:['11','7','13','5','4','3','16','24']
    }
  ]

  export const ImageMapper:any={
    '1':'/assets/img/VectorFLOW/NMS/AddRecords/sku-1.svg', 
    '5':'/assets/img/VectorFLOW/NMS/AddRecords/MOQ-1.svg',
    '4':'/assets/img/VectorFLOW/NMS/AddRecords/sob-1.svg',
    '2':'/assets/img/VectorFLOW/NMS/AddRecords/location-1.svg',
    '11':'/assets/img/VectorFLOW/NMS/AddRecords/seasonality.svg',
    '7':'/assets/img/VectorFLOW/NMS/AddRecords/phase-in-phase-out.svg',
    '13':'/assets/img/VectorFLOW/NMS/AddRecords/invest-1.svg',
    '3':'/assets/img/VectorFLOW/NMS/AddRecords/sku-location.svg',
    '27':'/assets/img/VectorFLOW/NMS/AddRecords/sku-1.svg',
    '15':'/assets/img/VectorFLOW/NMS/AddRecords/contact.svg',
    '26':'/assets/img/VectorFLOW/NMS/AddRecords/seasonality.svg',
    '20':'/assets/img/VectorFLOW/NMS/AddRecords/location-capacity.svg',
    '22':'/assets/img/VectorFLOW/NMS/AddRecords/location-priority.svg',
    '23':'/assets/img/VectorFLOW/NMS/AddRecords/location-priority.svg',
    '19':'/assets/img/VectorFLOW/NMS/AddRecords/location-1.svg',
    '21':'/assets/img/VectorFLOW/NMS/AddRecords/location-1.svg',
    '24':'/assets/img/VectorFLOW/NMS/AddRecords/pivot.svg',
    '25':'/assets/img/VectorFLOW/NMS/AddRecords/sku-1.svg', 
    '16':'/assets/img/VectorFLOW/NMS/AddRecords/deployment.svg',
    '18':'/assets/img/VectorFLOW/NMS/AddRecords/IST.svg',
    '17':'/assets/img/VectorFLOW/NMS/AddRecords/discount-period.svg',
}

export const ImageMapperHover:any={
    '1':'/assets/img/VectorFLOW/NMS/AddRecords/sku-1-hover.svg', 
    '5':'/assets/img/VectorFLOW/NMS/AddRecords/MOQ-1-Hover.svg',  
    '4':'/assets/img/VectorFLOW/NMS/AddRecords/sob-1-hover.svg',  
    '2':'/assets/img/VectorFLOW/NMS/AddRecords/location-1-hover.svg' ,
    '11':'/assets/img/VectorFLOW/NMS/AddRecords/seasonality-hover.svg',
    '7':'/assets/img/VectorFLOW/NMS/AddRecords/phase-in-phase-out-hover.svg',
    '13':'/assets/img/VectorFLOW/NMS/AddRecords/invest-1-hover.svg',
    '3':'/assets/img/VectorFLOW/NMS/AddRecords/sku-location-hov.svg',
    '27':'/assets/img/VectorFLOW/NMS/AddRecords/sku-1-hover.svg',
    '15':'/assets/img/VectorFLOW/NMS/AddRecords/contact-hover.svg',
    '26':'/assets/img/VectorFLOW/NMS/AddRecords/seasonality-hover.svg',
    '20':'/assets/img/VectorFLOW/NMS/AddRecords/location-capacity-hover.svg',
    '22':'/assets/img/VectorFLOW/NMS/AddRecords/location-priority-hover.svg',
    '23':'/assets/img/VectorFLOW/NMS/AddRecords/location-priority-hover.svg',
    '19':'/assets/img/VectorFLOW/NMS/AddRecords/location-1-hover.svg',
    '21':'/assets/img/VectorFLOW/NMS/AddRecords/location-1-hover.svg',
    '24':'/assets/img/VectorFLOW/NMS/AddRecords/pivot-hover.svg',
    '25':'/assets/img/VectorFLOW/NMS/AddRecords/sku-1-hover.svg',
    '16':'/assets/img/VectorFLOW/NMS/AddRecords/deployment-hover.svg',
    '18':'/assets/img/VectorFLOW/NMS/AddRecords/IST-hover.svg',
    '17':'/assets/img/VectorFLOW/NMS/AddRecords/discount-period-hover.svg'
}

export const TaskPendingAvoidColumnsMapper:any ={
    "1":["sc"],
    "2":['wc'],
    "3":['sc','wc'],
    "4":['sc','spc','wc'],
    "5":['sc','spc'],
    "6":['sc','wc'],
    "7":['sc','wc'],
    "8":['sc','wc','pi'],
    "9":['sc','wc'],
    "10":['sc','wc'],
    "11":['sc','wc'],
    "12":['sc','wc'],
    "13":['sc','wc']
}
export const TaskPendingAvoidColumnsMapperSpecific:any ={
    "1":["sd"],
    "2":['wd'],
    "3":['sd','wd'],
    "4":['sd','wd'],
    "5":['sd','wd'],
    "6":['posn','ln'],
    "7":['posn','ln'],
    "8":['ln','posn','pisn'],
    "9":['pisn','ln'],
    "10":['wd','skd'],
    "11":['skd','wd'],
    "12":['skd','wd'],
    "13":['sd','wd']
}
export const customKeys = [
    'c1',
    'c2',
    'c3',
    'c4',
    'c5',
    'c6',
    'c7',
    'c8',
    'c9',
    'c10',
    'c11',
    'c12',
    'c13',
    'c14',
    'c15'
]

export const mdmRoutes = [
    '/mta/master-data-management/control-panel/view-modify',
    '/mta/master-data-management/control-panel/add',
    '/mta/master-data-management/control-panel/delete'
]

export const TaskPendingStopPIPOCustomColumns:Array<ColDef | ColGroupDef> = [
    {
        colId:"t",
        headerName:"",
        field:'t',
        children:[
            {
              headerName:'Type',
              field:'type',
              colId:'type',
              valueFormatter:()=>"Stop-PIPO",
              cellStyle:{
                'text-align':'center',
                "border-right":"solid 1px #B9B9B9",
              }
            }
            
          ],
        
    },
    {
        colId:"norm",
        headerName:"Norm",
        field:'norm',
        children:[
            {
                colId:"targetNorm",
                headerName:"Target Norm",
                field:'targetNorm',
                cellStyle:{
                    "border-left":"solid 1px #B9B9B9",
                    'text-align':'center',
                    fontWeight:500
                }
            },
            {
                colId:"originalNorm",
                headerName:"Original Norm",
                field:'originalNorm',
                cellStyle:{
                    "border-right":"solid 1px #B9B9B9",
                    color:"Red",
                    'text-align':'center',
                    fontWeight:500
                }
            }
        ]
    },
    {
        colId:"r",
        headerName:"",
        field:'r',
        children:[
            {
                colId:"requestFor",
                headerName:"Request For",
                field:'requestFor',
                cellStyle:{
                    color:"Red",
                    fontWeight:500,
                    'text-align':'center',
                    "border-left":"solid 1px #B9B9B9",
                    "border-right":"solid 1px #B9B9B9",
                },
                valueFormatter:()=>"Stop"
            }
        ]
    },
    
]

export const CellDataTypeMapper:any = {
    "Boolean":"boolean",
    "Number":"number",
    "String":"text"
}