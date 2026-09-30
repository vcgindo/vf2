import { Allotment } from 'allotment'
import { useEffect, useState } from 'react'
import MTOActionToolBar from '../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar'
import { BTRAllomentSection, BTRTableWrapper, HorizontalViewWrapper } from '../../../Common/SplitGraphContainer/styles'
import IFFaildGraph from './IFFailedGraph'
import OTFailedGraph from './OTFailedGraph'
import { useGetOTAndIFAnalysisData, useGetOTAndIFAnalysisDataExcelExport } from '../../../../../../VectorFlow/Services/MTO/Poogi/InsightAndTrends/OTAndIFAnalysis'
import OverlayLoader from '../../../Common/Loader';
import { notifyError, notifySuccess } from '../../../../../../helpers/notify';
import GridView from '../../../Common/GridView'
import TagCellToolTip from '../../../Poogi/InsightAndTrends/OTIFAnalysis/TagCellRenderer/TagCellRenderer';
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import { useGetUIConfigData } from '../../../../../Services/MTO/Common/UIConfig';
import { DownloadExcel, formatFilterJSON, getBodyForExcelExport, getColumnDefinations } from '../../../../../../helpers/utils';
import { useUserData } from "../../../../../../context/index";
import { FilterPageName, pagination, UIGridCode } from "../../../Common/Enum";
import useFilter from '../../../../../../hooks/useFilter'
import { useGetFilterData } from '../../../../../../VectorFlow/Services/MTO/Common/CommonFilter'
import useColDef from '../../../../../../hooks/useColDef'
import BPPRenderer from '../../../Common/BPRRenderer/BPPRenderer'
import moment from 'moment'

const APIFilterConfig = {
    filSecVisConfig: {
        "Poogi_OTIF_And_Analysis" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
    }
};

const OTAndIFAnalysis = () => {

    const [isGridView, setIsGridView] = useState(false);
    const { mutateAsync: getOTAndIFAnalysisData, isLoading, isError, isSuccess } = useGetOTAndIFAnalysisData();
    const [graphData, setGraphData] = useState<any>({});
    const [currentGridRef, setCurrentGridRef] = useState<any>(null);
    const [columnState, setColumnState] = useState<any>([]);
    const [isReset, setIsReset] = useState<any>(undefined);
    const [colDef, setColDef] = useState([{}]);
    const [HeaderData, setHeaderData] = useState([]);
    const [filterData, setFilterData] = useState({});
    const { mutateAsync: getPageWiseFilterData, /*isLoading*/ } = useGetFilterData()
    const { 
        state: currFilter, 
        setState: setCurrFilter, 
        onFilterRemove, 
        isFilterOpen, 
        isMfgSelected,
        onAddFilter, 
        onApplyFilter, 
        toggleFilter,
        appliedFilters
    } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Poogi_OTIF_And_Analysis);
    const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
    const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
    const { mutateAsync: getUIConfigData } = useGetUIConfigData()
    const { user } = useUserData();
    const { colDefMap , getColDef} = useColDef();
    const { mutateAsync: getOTAndIFAnalysisDataExcelExport } = useGetOTAndIFAnalysisDataExcelExport();
    const [masterUIConfig, setMasterUIConfig] = useState([]);

    const [userPageSize, setUserPageSize] = useState<number>();
    const [userConfigFetched, setUserConfigFetched] = useState(false);
    
    const getGraphData = async (params: any,pageSize?:any) => {

        if(params.isExcelExport){

            const gridAPi = currentGridRef?.current?.api;

            if (!gridAPi) {
                notifyError('Grid is not ready for Excel export!');
                return;
            }

            const isPivot = gridAPi.isPivotMode(); 
            const isValue = gridAPi.getValueColumns().length > 0;
            const isRowGroup = gridAPi.getRowGroupColumns().length > 0;
            console.log("isPivot:, isValue:, isRowGroup:", isPivot, isValue, isRowGroup);  

            if(isPivot || isValue || isRowGroup){
                const exportName = `${FilterPageName.Poogi_OTIF_And_Analysis}_${moment().format("DD-MM-YYYY")}`;
                
                gridAPi.exportDataAsExcel({
                    fileName: exportName,
                    sheetName: exportName
                })
                
            } else {
                const headersdata = currentGridRef?.current?.api.getColumnState();
                const formattedFilters = formatFilterJSON(appliedFilters);
                const body = getBodyForExcelExport({ headersdata, filterData: formattedFilters,colDefMap})
                const response = await getOTAndIFAnalysisDataExcelExport({body, isExcelExport : 1, graphflag : 0,report_name : FilterPageName.Poogi_OTIF_And_Analysis})
                if(response.status === 200){
                    DownloadExcel(response, FilterPageName.Poogi_OTIF_And_Analysis)
                }else{
                    notifyError('Failed to export Excel!');
                }
            }        
        }else{
            try {
                const response = await getOTAndIFAnalysisData({
                    ...params
                });
                setGraphData(response.data.data);
            }
            catch (e) {
                console.log(e);
                notifyError('Failed to fetch Graph data!');
            }
        }
    }

    const colDefCustomizations = {
        Tags: {
            tooltipValueGetter: (params: any) => params.value,
            cellRenderer: TagCellToolTip,
            cellStyle: {
                display: 'flex',
                justifyContent: "center",
            },
            minWidth:100,
        },
        BPP: {
            cellRenderer: BPPRenderer,
            minWidth:100,
        },
    }

    const getUserColumnConfig = async () => {
        try {
            const data = await getUserUIReportConfigData({
                un: user.user.name,
                rn_id: UIGridCode.PoogiOTAndIFAnalysis
            });

            setUserConfigFetched(true);
            const newConfig = data?.data?.data[0]? JSON.parse(data?.data?.data[0]?.columns_settings) || [] : [];
            setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : pagination.mtoPageSize);
            setColumnState(newConfig.cs);
            
        } catch (error) {
            console.error(error);
        }
    }

    const setColumnDef = async () => {
        try {
            const response = await getUIConfigData('OTIFAnalysis');
            getColDef(response);
            setHeaderData(response?.data?.data);
        }
        catch (e) {
            console.log(e);
        }
    }

    useEffect(() => {
        getFilterData();
    }, []);
    
    const handleSaveClick = async (coldefs?: any, page_size?: number) => {
        try {
            if (coldefs) {
                const fullConfig = { 
                    cs: coldefs, 
                    pageSize: userPageSize 
                };
                const payload = {
                    un: user.user.name,
                    rn_id: UIGridCode.PoogiOTAndIFAnalysis,
                    cs: JSON.stringify(fullConfig),
                };
                await updateUserUIReportConfigData([payload]);
                setColumnState([...coldefs]);
            } 
            else if (page_size) {
                const config = columnState;
                const fullConfig = { cs: config, pageSize: page_size };
                const payload = {
                    un: user.user.name,
                    rn_id: UIGridCode.PoogiOTAndIFAnalysis,
                    cs: JSON.stringify(fullConfig),
                };
                
                await updateUserUIReportConfigData([payload]);
            }
            else {
                if (currentGridRef?.current?.api) {
                    const config = currentGridRef.current.api.getColumnState();
                    const fullConfig = { cs: config, pageSize: userPageSize };
                    
                    const payload = {
                        un: user.user.name,
                        rn_id: UIGridCode.PoogiOTAndIFAnalysis,
                        cs: JSON.stringify(fullConfig)
                    };
                    await updateUserUIReportConfigData([payload]);
                    await getUserColumnConfig();
                }
            }
        } catch (error) {
            console.error(error);
        }
    }

    const handleResetClick = () => {
        setIsReset(true);
    }

    const getFilterData = async () => {
        try {
          const response = await getPageWiseFilterData({ page_name: FilterPageName.Poogi_OTIF_And_Analysis });
          setFilterData(response?.data.data);
        } catch (error) {
          console.error(error);
        }
    }

    useEffect(() => {
        if (HeaderData.length > 0) {
            setColDef(getColumnDefinations(HeaderData, colDefCustomizations))
        }
    }, [HeaderData])

    useEffect(() => {
        getGraphData({ graphflag: 1 }, userPageSize || pagination.mtoPageSize);
        setColumnDef();
    }, [])

    useEffect(() => {
        if (isSuccess) {
          notifySuccess("Fetched Data successfully!")
        }
        if (isError) {
          notifyError("Failed to load data!")
        }
    }, [isSuccess, isError])

    useEffect(() => {
        if (isReset) {
            handleSaveClick(masterUIConfig);
            setIsReset(false);
        }
    }, [isReset]);

    
    useEffect(() => {
        if (currentGridRef?.current) {
            getUserColumnConfig();
            setMasterUIConfig(currentGridRef?.current.api.getColumnState());
        }
    }, [colDef, currentGridRef]);

    

    const ExportExcelData = () =>{
        getGraphData({ isExcelExport: true });
    }

    const themeUi = user?.user?.theme_ui;

    return (
        <>
            {
                (isLoading|| isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />
            }
            <MTOActionToolBar
                isAddFilterButton
                isChartGridToggle
                themeUi={themeUi}
                setIsGridView={setIsGridView}
                isExcelExport = {isGridView ? true : false}
                onExcelExportClick ={ExportExcelData}
                isGridView={isGridView}
                handleSaveClick={handleSaveClick}
                handleResetClick={handleResetClick}
                isFilterOpen={isFilterOpen}
                onAddFilter={onAddFilter}
                toggleFilter={toggleFilter}
                onApplyFilter={onApplyFilter}
                multiFilter={currFilter}
                setMultiFilter={setCurrFilter}
                onFilterRemove={onFilterRemove}
                isMfgSelected={isMfgSelected}
            />
            {
                !isGridView ?
                    <>
                        <HorizontalViewWrapper style={{ margin: '20px 14px', height: '85%', display: 'flex' }}>
                            <BTRTableWrapper style={{ flex: '1', margin: '0' }}>
                                <Allotment vertical={false} separator={false}   >
                                    <Allotment.Pane minSize={400} preferredSize={'50%'} className='allotment-pane-custom'>
                                        <BTRAllomentSection>
                                            <OTFailedGraph OTFailedData={graphData?.ot} />
                                        </BTRAllomentSection>
                                    </Allotment.Pane>
                                    <Allotment.Pane minSize={400} preferredSize={'50%'} className='allotment-pane-custom'>
                                        <BTRAllomentSection>
                                            <IFFaildGraph IFFailedData={graphData?.if} />
                                        </BTRAllomentSection>
                                    </Allotment.Pane>
                                </Allotment>
                            </BTRTableWrapper>
                        </HorizontalViewWrapper>
                    </>
                    :
                    <>
                        <GridView
                            getData={(params: any) => getOTAndIFAnalysisData({
                                ...params
                            })}
                            colDef={colDef}
                            isLoading={isLoading}
                            isError={isError}
                            isSuccess={isSuccess}
                            setCurrentGridRef={setCurrentGridRef}
                            currentGridRef={currentGridRef}
                            columnState={columnState}
                            appliedFilters={appliedFilters}
                            userPageSize={userPageSize}
                            setUserPageSize={setUserPageSize}
                            userConfigFetched={userConfigFetched}
                            handleSaveClick={handleSaveClick}
                        />
                    </>
            }
        </>
    )
}

export default OTAndIFAnalysis