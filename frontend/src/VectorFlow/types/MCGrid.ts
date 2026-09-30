
  export interface DefaultStoreDataType {
    stores:number
    "grid-points":number
    contribution:number
    details:StoreDetails
}

export interface StoreDetails{
    sales:{
        value:number
        pcs:number
    },
    "gross-margin":{
        value:number
        pcs:number
    },
    "planned-range":{
        value:number
        pcs:number
    },
    "range-available":{
        value:number
        pcs:number
    },
    "gap":{
        value:number
        pcs:number
    }
}

export interface FloatingStoreDataType {
    contribution:number
    initial:{
        "grid-points":number,
        stores:number
    }
    available:{
        stores:number
        "grid-points":number,
        details:{
            sales:{
                value:number
                pcs:number
            },
            "gross-margin":{
                value:number
                pcs:number
            },
            "planned-range":{
                value:number
                pcs:number
            },
            "range-available":{
                value:number
                pcs:number
            },
            "gap":{
                value:number
                pcs:number
            }
        }
    }
    
}



  export interface GridHealthType {
    surplus: {
      low: DefaultStoreDataType;
      medium: DefaultStoreDataType;
      high: DefaultStoreDataType;
    };
    complete: {
      low: DefaultStoreDataType;
      medium: DefaultStoreDataType;
      high: DefaultStoreDataType;
    };
    incomplete: {
      low: FloatingStoreDataType;
      medium: FloatingStoreDataType;
      high: FloatingStoreDataType;
    };
    'very-incomplete': {
      low: FloatingStoreDataType;
      medium: FloatingStoreDataType;
      high: FloatingStoreDataType;
    };
  }
  
  export type TableLabelStatus = "low" | "medium" |  "high" | "surplus" | "complete" | "incomplete" | "very-incomplete"

  export interface TableLabelProps  {
      text:string
      status: TableLabelStatus
  }