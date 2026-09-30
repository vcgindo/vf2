import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { useGetOpenSODetailsData, useGetOpenSODetailsDataForExcelExport, useGetSOSummaydetails } from '../../../../../VectorFlow/Services/MTO/Procurement/MaterialCoverage';
import ActionToolBar from "../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import VFFloatingTab from "../../../../../components/VectorFLOW/commons/VFFloatingTab";
import { notifyError, notifyLoader } from '../../../../../helpers/notify';
import useFilter from "../../../../../hooks/useFilter";
import { MaterialCoverageString } from '../../Common/String';
import {
  BTRLayoutTabsWrapper,
  ProcurementLayout,
  TextXAxis,
  TextYAxis,
} from '../MaterialCoverage/styles';
import { DetailsObj } from './CommonFunc';
import CurrentCov from './CurrentCov';
import FutureCov from './FutureCov';
import { useGetFilterData } from '../../../../../VectorFlow/Services/MTO/Common/CommonFilter';
import { useGetDBRsettingsData } from '../../../../../VectorFlow/Services/MTO/Common/DBRSettings';
import VFButton from '../../../../../components/VectorFLOW/commons/VFButton';
import { useUserData } from "../../../../../context/index";
import CommonGridview, { getExcelExportDataArgs, getRowDataArgs } from '../../../../../helpers/CommonGridview';
import { getColumnDefinations } from '../../../../../helpers/utils';
import useColDef from '../../../../../hooks/useColDef';
import { useGetUIAndUserConfigData } from '../../../../Services/MTO/Common/UIConfig';
import BomExcelModal from '../../Common/BomExcelModal';
import ChildrenColor from "../../Common/ChildrenColor/ChildrenColor";
import ColorCellRenderer from "../../Common/ColorCellRenderer/ColorCellRenderer";
import { FilterPageName, UIGridCode } from "../../Common/Enum";
import OverlayLoader from '../../Common/Loader';
import CustomGroupCellRenderer from "./CustomGroupCellRenderer";
import useMaterialSO from './useMaterialSO';



const APIFilterConfig = {
  filSecVisConfig: {
    "Proc_Material_Coverage_For_OpenSO": {
      mjr: false,
      or: true,
      res: true,
      cus: true
    },
  }
};

const MaterialCov = () => {
  const [detailDataObj, setDetailDataObj] = useState<DetailsObj>();
  const [currTab, setCurrTab] = useState<string>("CurrentCoverage");
  const [toggleComponent, setToggleComponent] = useState<boolean>(false);
  const [soData, setSOData] = useState<any>([]);
  const { mutateAsync: getSOSummaryData, isLoading, /*refetch*/ } = useGetSOSummaydetails();
  const { mutateAsync: getPageWiseFilterData, /*isLoading*/ } = useGetFilterData();
  const [filterData, setFilterData] = useState({});
  
  const { mutateAsync: getOpenSODetailsData, isLoading: gridDataLoading} = useGetOpenSODetailsData()
  const { mutateAsync : getOpenSODetailsDataForExcelExport } = useGetOpenSODetailsDataForExcelExport();
  const { user } = useUserData();
  const {  getNewColDef} = useColDef();

  const {mutateAsync: getDBRsettingsData} = useGetDBRsettingsData();
  const [childColDef, setChildColDef] = useState<any>();
  
  const [isAllData, setIsAllData] = useState(false);
  
    const reportName = detailDataObj?.allOrders ? "MaterialCoverageforOpenSalesAllOrders" :'MaterialCoverageforOpenSalesOrder';
    const childReportName = "MaterialCoverageforOpenSalesOrder_Child"
  
    const { 
    state: currFilter, 
    setState: setCurrFilter, 
    onFilterRemove, 
    isFilterOpen,
    isMfgSelected, 
    onAddFilter, 
    onApplyFilter, 
    toggleFilter,
    appliedFilters,
    setAppliedFilters,
  } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Proc_Material_Coverage_For_OpenSO);

  const {
    agGridProps,
    getInitialDataQuery,

} = useMaterialSO(detailDataObj, childColDef);



    const themeUi = user?.user?.theme_ui;
    
    const tabs = [
      {
        id: "1",
        value: 'CurrentCoverage',
        label: "Current Coverage"
      },
      {
        id: "2",
        value: 'FutureCoverage',
        label: "Future Coverage"
      }
    ]
  
    const defaultTab = tabs.findIndex(tab => tab.value === currTab)

  useEffect(() => {
    if (isLoading) {

      toast.dismiss();
      notifyLoader("Loading Data ...")
    }
    else {
      toast.dismiss();
    }
  }, [isLoading])


  const handleToggleComponent = (value: boolean) => {
    setToggleComponent(value);

    
  }

  const handleParameterData = (data: any) => {
    setDetailDataObj(data)
  }

  const getSOData = async () => {
    try {
      const response = await getSOSummaryData();
      setSOData(response?.data?.data || []);
    } catch (error) {
      console.log(error);
      notifyError('Failed to fetch Grid data!');
    }
  }

  useEffect(() => {
      getSOData();
  }, []);


    const { mutateAsync: getUIAndUserConfigData  } =
      useGetUIAndUserConfigData();

  const setColumnDef = async () => {
      try {
        const response = await getUIAndUserConfigData({
          reportName:childReportName,
          userName: user.user.name,
          reportNameId:UIGridCode.ProcMaterialCovOpenSales,
        });
        const defaultColDef = response?.data?.data?.default_coldef;
      
        getNewColDef(response);
        setChildColDef(
          getColumnDefinations(
            defaultColDef,
            childCustomheader
          )
        );
  
       
      } catch (e) {
        console.log(e);
      }
    };


  const customHeader =
  {
      ColorPriority: {
          cellRenderer: ColorCellRenderer
      },
      FullKitAvail: {
          minWidth: 150,
          cellStyle: {
              paddingRight: '25px'
          },
        cellRenderer: "avlCellRenderer",
          tooltipComponent: 'availabilityToolTip',
          tooltipValueGetter: (params: any) => {
              const oq = params.data.oq;
              const fka = params.data.fka;
              return `${fka}/${oq} kits can be manufactured`;
          },
      },
      fk_status : {
        pinned: 'right',
        lockPinned: true,
        suppressMovableColumns:true,
      }
  }

  const childCustomheader = {
    clr:{
      cellRenderer : ChildrenColor
    }
  }

  const extras = [
      {
          field: "",
          resizable: true,
          position: 0,
          suppressHeaderFilterButton: true,
          suppressMenu: true,
          filter: false,
          width: 50,
          maxWidth: 50,
          pinned:"left",
          cellRenderer: CustomGroupCellRenderer
      }
  ]

  const getFilterData = async () => {
    try {
      const response = await getPageWiseFilterData({page_name: FilterPageName.Proc_Material_Coverage_For_OpenSO});
      setFilterData(response?.data.data);
    } catch (error) {
      console.error(error);
    }
  }


  useEffect(() => {
    // getHeaderData();
    setColumnDef()
    getFilterData()
  }, [])


  


  const getSettingsData = async()=>{
    const DBRSettingsData: any = await getDBRsettingsData()
    const DBRSettings = DBRSettingsData.data?.data;

    for(const setting of DBRSettings){
      if(setting.flag === "MaterialSOAllData"){
          setIsAllData(setting.value == 1 ? true : false)
      }
  }
  }

  useEffect(()=>{
    getSettingsData()
  },[])

  type ExportModalProps = {
    onConfirm: () => void;
    onCancel: () => void; 
    onClose: () => void;
    showExcelModal : boolean;
  };
  
  const BomExcelExportModal = ({
    onConfirm,
    onCancel,
    onClose,
    showExcelModal,
  }: ExportModalProps) => {
    return (
      <BomExcelModal
        open={showExcelModal}
        onClose={onClose}
        onConfirm={onConfirm}
        onCancel={onCancel}
        themeUi={themeUi}
        headerText="Excel Export"
        messageText="Do you want to download Excel with RM/PM details?"
      />
    );
  };

  return (
    <div style={{ width: "100%", height: "100%" }}>
      {!toggleComponent ? (
        <>
          {isLoading && <OverlayLoader />}

          <ActionToolBar
            comp={"MaterialCov"}
            themeUi={themeUi}
          />
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: isAllData ? "right" : "center",
                alignItems: "center",
                width: "100%",
                padding: "0 1rem",
              }}
            >
              <BTRLayoutTabsWrapper>
                <VFFloatingTab
                  handleClick={(e) => setCurrTab(e.value)}
                  tabs={tabs}
                  defaultTab={defaultTab}
                />
              </BTRLayoutTabsWrapper>

              {isAllData && (
                <VFButton
                  style={{
                    marginLeft: "30%",
                    fontSize: "10px",
                    height: "30px",
                    fontFamily: "roboto",
                  }}
                  themeUi={themeUi}
                  onClick={() => {
                    handleToggleComponent(true),
                      handleParameterData({ allOrders: true });
                  }}
                >
                  Show All Orders
                </VFButton>
              )}
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                width: "100%",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "max-content",
                  position: "relative",
                }}
              >
                <TextXAxis
                  style={{
                    height: "max-content",
                    position: "absolute",
                    right: "100%",
                  }}
                >
                  {MaterialCoverageString.orderPriority}
                  <div
                    style={{
                      width: "85%",
                      border: "1px solid #000",
                      color: "#FFFFFF",
                      marginBottom: "10px",
                      marginLeft: "5px",
                    }}
                  ></div>
                </TextXAxis>

                {/**code goes here */}
                {currTab === "FutureCoverage" ? (
                  <FutureCov
                    handleToggleComponent={handleToggleComponent}
                    setDetailDataObj={handleParameterData}
                    data={soData}
                  />
                ) : (
                  <CurrentCov
                    handleToggleComponent={handleToggleComponent}
                    setDetailDataObj={handleParameterData}
                    data={soData}
                  />
                )}
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "center" }}>
              <TextYAxis style={{ width: "max-content" }}>
                {MaterialCoverageString.statusKits}
                <div
                  style={{
                    width: "85%",
                    border: "1px solid #000",
                    color: "#FFFFFF",
                    marginBottom: "8px",
                    marginLeft: "5px",
                  }}
                ></div>
              </TextYAxis>
            </div>
          </div>
        </>
      ) : (
        <div
          style={{
            height: "100%",
            display: "flex",
            flexDirection: "column",
            paddingBottom: "2rem",
          }}
        >
          <CommonGridview
            reportName={reportName}
            columnDefinationProps={{
              customColDef: customHeader,
              extras: extras,
            }}
            gridDataLoading={gridDataLoading}
            excelExportParams={{
              isExcelExportFromBackend: true,
              excelExportReportName: reportName,
              showBomExcelModal: true,
              excelExportSheetName: reportName,
            }}
            customGridOptions={agGridProps}
            setAppliedFilters={setAppliedFilters}
            setCurrentFilters={setCurrFilter}
            appliedFilters={appliedFilters}
            reportNameId={UIGridCode.ProcMaterialCovOpenSales}
            getExcelExportData={(params: getExcelExportDataArgs) => {
              const queryString = getInitialDataQuery({
                isChildren: params.isChildren,
                isExcelExport: true,
              });
              return getOpenSODetailsDataForExcelExport({
                data: queryString,
                ...params,
              });
            }}
            getRowData={(params: getRowDataArgs) => {
              const queryString = getInitialDataQuery({
                currPage: params.page,
                pageSize: params.page_size,
              });
              return getOpenSODetailsData({
                data: queryString,
                appliedFilters: params?.appliedFilters,
              });
            }}
            actionToolBarProps={{
              comp: "MaterialCovDetailData",
              isAddFilterButton: true,
              isGoBackButton: true,
              handleGoBack: () => {
                handleToggleComponent(false);
              },
              isFilterOpen: isFilterOpen,
              onAddFilter: onAddFilter,
              toggleFilter: toggleFilter,
              onApplyFilter: onApplyFilter,
              isMfgSelected: isMfgSelected,
              multiFilter: currFilter,
              setMultiFilter: setCurrFilter,
              onFilterRemove: onFilterRemove,
            }}
            BomExcelExport={BomExcelExportModal}
            VFWrapper={ProcurementLayout}
            vfWrapperStyle={{ marginLeft: '25px', flex: "1" }}
          />

        </div>
      )}
    </div>
  );
}
export default MaterialCov;