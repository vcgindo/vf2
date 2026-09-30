import GridViewTable from "../../../SupplyChainIntelligenceHub/Planning/GridView/GridViewTable";
import { AgGridReactProps } from "ag-grid-react";
import {
  getColumnDefinationsMTA,
  MainMenuItemsCustomization,
} from "../../../../../../helpers/utils";
import React, { Fragment, useEffect, useRef, useState } from "react";
import { useGetUIConfigData } from "../../../../../Services/MTA/Common/UIConfig";
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../../helpers/Enum";
import { notifyError } from "../../../../../../helpers/notify";
import { ColDef } from "ag-grid-enterprise";
import { useSelector } from "react-redux";
import { RootState } from "../../../../../../redux/store/store";



interface ChronicGridViewProps {
  currentGridData: any;
}
const ChronicGridView = ({ currentGridData }: ChronicGridViewProps) => {
  const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
  const { mutateAsync: getUiConfig } =
    useGetUIConfigData();
  const [ChronicUnavailabilityColumns, setChronicUnavailabilityColumns] =
    useState<ColDef[]>([]);

  useEffect(() => {
    getMasterUiConfig();
  }, []);

  const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
  const GUIDEDINSIGHT_ROWS_PER_PAGE = EnvConfig['GUIDEDINSIGHT_ROWS_PER_PAGE']; 

  const getMasterUiConfig = async () => {
    try {
      const response = await getUiConfig(UIColumnConfigName.ChronicUnavailability);
      setInitialColumnState(response.data.data);
    } catch (err: any) {
      notifyError("Something Went Wrong");
    }
  };

  useEffect(() => {
    const getTableState = async () => {
      try {
        const MappedColumns = getColumnDefinationsMTA(
          initialColumnState,
          CustomHeader
        );
        setChronicUnavailabilityColumns(MappedColumns);
      } catch (err: any) {
        console.log(err);
      }
    };
    if (initialColumnState !== undefined) {
      getTableState();
    }
  }, [initialColumnState]);

  const CustomHeader = {
    location: {
      rowGroup: true,
    }
  };

 

  

  const sideBarForChronicGrid = {
    toolPanels: [
      {
        id: "columns",
        labelDefault: "Columns",
        labelKey: "columns",
        iconKey: "columns",
        toolPanel: "agColumnsToolPanel",
        // toolPanelParams: {},
        toolPanelParams: {
          suppressPivots: true,
          suppressPivotMode: true,
          suppressRowGroups: true,
          suppressValues: true,
        }
      }
    ],
    defaultToolPanel: "",

  };

  const agGridProps: AgGridReactProps = {
    paginationPageSize: parseInt(
      GUIDEDINSIGHT_ROWS_PER_PAGE || "50"
    ),

    suppressRowTransform: true,
    tooltipShowDelay: 0.3,
    tooltipTrigger: "focus",
    tooltipInteraction: true,
    readOnlyEdit: true,
    gridOptions: {
      sideBar: sideBarForChronicGrid,
      rowHeight: 50,
      getRowStyle: (params: any) => {
        if (params.node.rowIndex % 2 === 0) {
          return { background: "#EBEBEB" };
        }
        return { background: "#F7F7F7" };
      },
    },
    getMainMenuItems: MainMenuItemsCustomization,
    enableRangeSelection: true,
    rowSelection: "multiple",
    statusBar: {
      statusPanels: [
        { statusPanel: "agTotalAndFilteredRowCountComponent", align: "left" },
        { statusPanel: "agTotalRowCountComponent", align: "left" },
        { statusPanel: "agFilteredRowCountComponent", align: "left" },
        { statusPanel: "agSelectedRowCountComponent", align: "left" },
        { statusPanel: "agAggregationComponent", align: "left" },
      ],
    },
    pagination: true,
    suppressRowClickSelection: true,
    defaultColDef: {
      flex:1,
      floatingFilter: true,
      filter: "agMultiColumnFilter",
      cellDataType: false,
      resizable: true,
      minWidth:150,
      cellStyle: {
        textAlign: "center",
        height: "50px",
        fontStyle: "normal",
        " fontVariant": "normal",
        " fontWeight": "300",
        " fontSize": "20px",
        " fontFamily": "Roboto",
        display: "block",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
      },
    },
  };

  const PlanningColumns = [
    {
      colId: "skucode",
      field: "skucode",
      headerName: "skucode",
      enablePivot: true,
    },
    {
      colId: "location",
      field: "location",
      headerName: "location",
      enablePivot: true,
      rowGroup: true,
    },
    {
      colId: "skudesc",
      field: "skudesc",
      headerName: "skudesc",
      enablePivot: true,
    },
    {
      colId: "parentloc",
      field: "parentloc",
      headerName: "parentloc",
      enablePivot: true,
    },
    { colId: "RLT", field: "RLT", headerName: "RLT", enablePivot: true },
    {
      colId: "BlackRedAgeing",
      field: "BlackRedAgeing",
      headerName: "BlackRedAgeing",
      enablePivot: true,
    },
    {
      colId: "Executive",
      field: "Executive",
      headerName: "Executive",
      enablePivot: true,
    },
    {
      colId: "Techcolor",
      field: "Techcolor",
      headerName: "Techcolor",
      enablePivot: true,
    },
    {
      colId: "ExecutiveEco",
      field: "ExecutiveEco",
      headerName: "ExecutiveEco",
      enablePivot: true,
    },
    {
      colId: "ecocolor",
      field: "ecocolor",
      headerName: "ecocolor",
      enablePivot: true,
    },
    {
      colId: "RationedStockatparent",
      field: "RationedStockatparent",
      headerName: "RationedStockatparent",
      enablePivot: true,
    },
  ];

  return (
    <div style={{padding:"20px 0px 0px 20px"}}>
      <GridViewTable
        agGridProps={agGridProps}
        agGridColDefs={ChronicUnavailabilityColumns}
        agGridRowData={currentGridData}
        customGridRowData={[]}
        customGridColDef={[]}
        isSubGridOpen={false}
        currentCategory={"GuidedInsightchronicunavailability"}
        currentTab={""}
        gridHeight={"80%"}
        
      />
    </div>
  );
};
export default ChronicGridView;
