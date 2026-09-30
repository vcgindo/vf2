import { SideBarDef } from "ag-grid-enterprise";
import { AgGridReactProps } from "ag-grid-react";
import { useMemo } from "react";
import { notifyError } from "../../../../../helpers/notify";
import AvailabilityToolTip from "../../../../../VectorFlow/Pages/MTA/InsightsAndTrends/BTR/AvailabilityToolTip";
import AvlCellRenderer from '../../Common/AvlCellRenderer/AvlCellRenderer';
import ColorCellRenderer from "../../Common/ColorCellRenderer/ColorCellRenderer";
import { pagination } from "../../Common/Enum";
import CustomGroupCellRenderer from "./CustomGroupCellRenderer";
import DetailCellRenderer from "./MaterialCellRenderer";

const useMaterialSO = (data: any,  childColDef: any) => {

  type getInitialDataQueryArgs = {
    currPage?: number;
    pageSize?: number;
    isChildren?: number;
    isExcelExport?: boolean;
  }

  const getInitialDataQuery =  ({currPage,pageSize,isChildren=0,isExcelExport=false}: getInitialDataQueryArgs) => {
        try {
            const colorsArray = Object.keys(data).filter((k: string) => k.startsWith('c'));
            const colorsQuery = colorsArray.map((key: string) => data[key]).join(',');
          let queryString = '';
          if (isExcelExport) {
            queryString = `?Color=${colorsQuery}&KitStatus=${data.kit}&S=${data.S}&E=${data.E}&isChildren=${isChildren}`;
            if(data.allOrders){
              queryString = `?AOD=${true}&isChildren=${isChildren}`
            }
         
          } else {
            queryString = `?Color=${colorsQuery}&KitStatus=${data.kit}&S=${data.S}&E=${data.E}&page=${currPage}&page_size=${pageSize  || pagination.mtoPageSize}`;
        
            if(data.allOrders){
              queryString = `?AOD=${true}&page=${currPage}&page_size=${pageSize || pagination.mtoPageSize}`
            }
            
            
          }
          return queryString;
        } catch (error) {
          notifyError(`An error occurred while fetching data : ${error}`);
        } 
      }


    const autoGroupColumnDef = useMemo(() => {
        return {
            minWidth: 250,
        };
    }, []);
    const sideBar:SideBarDef = {
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
   
    const customCellRenderers = useMemo(() => (
        {
            "colorCellRenderer": ColorCellRenderer,
            "avlCellRenderer": AvlCellRenderer,
            "availabilityToolTip": AvailabilityToolTip,
            "customGroupCellRenderer": CustomGroupCellRenderer

        }), []);

    const agGridProps: AgGridReactProps = {
        tooltipShowDelay: 0,
        tooltipTrigger: "focus",
        gridOptions: {
            rowHeight: 50,
            getRowStyle: (params: any) => {
                return {
                    background: params.node.rowIndex % 2 === 0 ? "#EBEBEB" : "#F7F7F7"
                };
            },
            pagination: true,
            rowSelection: 'multiple',
            suppressRowClickSelection: true,
            enableBrowserTooltips: true,
            enableRangeSelection: true,
          components: customCellRenderers,
            
          defaultColDef: {
                
                resizable: true,
                initialFlex: 1,
                filter: 'agTextColumnFilter',
                floatingFilter: true,
                cellStyle: {
                    'text-align': 'center',
                    'height': '50px',
                    "font-style": "normal",
                    "font-variant": "normal",
                    "font-weight": "300",
                    "font-size": "20px",
                    "font-family": "Roboto",
                    'text-overflow': 'ellipsis',
                    'white-space': 'nowrap',
                    'resizable': 'true',
                },

            },
        },
        
        sideBar: sideBar,
        masterDetail: true,
        detailCellRenderer: DetailCellRenderer,
        detailCellRendererParams:{
            colDef : childColDef
        },
        detailRowHeight: 240,
        autoGroupColumnDef: autoGroupColumnDef,
        paginationAutoPageSize: true,

        enterNavigatesVertically: true,
        enterNavigatesVerticallyAfterEdit: true,
    };


    return {
        agGridProps,
        getInitialDataQuery,
    }
}

export default useMaterialSO;