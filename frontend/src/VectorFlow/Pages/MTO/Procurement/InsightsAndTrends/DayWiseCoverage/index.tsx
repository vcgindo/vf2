import React, { useEffect, useMemo, useState } from 'react'
import DayWiseCoverageCalender from './DayWiseCoverageCalender';
import DayWiseCoverageHeader from './DayWiseCoverageHeader'
import DayWiseCoverageTable from './DayWiseCoverageTable';
import { Player } from '@lottiefiles/react-lottie-player';
import { AnimationWrapper, HelperText, TableContainer } from './style';
import MTOActionToolBar from '../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar';
import { add, eachMonthOfInterval, endOfMonth, format, getMonth, startOfMonth } from 'date-fns';
import { useGetDayWiseCoverageData } from '../../../../../../VectorFlow/Services/MTO/Procurement/DayWiseCoverage';
import OverlayLoader from '../../../Common/Loader';
import { useDispatch } from 'react-redux';
import { DAYWISE_COVERAGE_ANALYTICS } from '../../../../../../redux/actions/MTO';
import VFModalCard from '../../../../../../components/VectorFLOW/commons/VFModalCard';
import MaterialRequirementComponent from '../../MaterialRequirement/MaterialRequirementComponent';
import useMaterialReq from '../../MaterialRequirement/useMaterialRequirements';
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import { UIGridCode } from "../../../Common/Enum";
import { useUserData } from "../../../../../../context/index";
import { useGetUIConfigData } from "../../../../../../VectorFlow/Services/MTO/Common/UIConfig";
import { getColumnDefinations } from "../../../../../../helpers/utils";
import ColorCellRenderer from "../../../Common/ColorCellRenderer/ColorCellRenderer";
import VFLoader from '../../../../../../components/VectorFLOW/commons/VFLoader';
// import { useGetFilterData } from '../../../../../..//VectorFlow/Services/MTO/Common/CommonFilter';
// import useFilter from '../../../../../../hooks/useFilter';

enum Colors {
    Selected = "#B93B7E",
    NoData = "lightgrey",
    Green = "#33800B",
    Red = "#F02424"
}

// const APIFilterConfig = {
//     filSecVisConfig: {
//         "Proc_Day_Wise_Coverage" : {
//             mjr : false,
//             or: false,
//             res: true,
//             cus: true
//         },
//     }
//   };

const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

const DayWiseCoverage = () => {
    // const currentMonth = format(new Date(), "yyyy-MM");
    const minDate = useMemo(() => startOfMonth(add(new Date(), { months: -2 })), [])
    const maxDate = useMemo(() => endOfMonth(new Date()), []);

    const [startDate, setStartDate] = useState(format(minDate, "yyyy-MM"));
    const [endDate, setEndDate] = useState(format(maxDate, "yyyy-MM"));
    const [selectedDate, setSelectedDate] = useState<string>("");
    const [showModal, setShowModal] = useState<boolean>(false);

    const [calenderData, setCalenderData] = useState<any>();

    const [loading, setLoading] = useState(false);
    const [currentGridRef, setCurrentGridRef] = useState<any>(null);
    const [columnState, setColumnState] = useState<any>([]);
    const [isReset, setIsReset] = useState(false);
    const [colDef, setColDef] = useState([]);
    // const [filterData, setFilterData] = useState({});
    const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
    const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
    const { mutateAsync: getData, isLoading: isCalenderLoading } = useGetDayWiseCoverageData();
    const { mutateAsync: getUIConfigData } = useGetUIConfigData();
    const [masterUIConfig, setMasterUIConfig] = useState([]);

    // const { mutateAsync: getPageWiseFilterData, /*isLoading*/ } = useGetFilterData()
    // const { 
    //     state: currFilter, 
    //     setState: setCurrFilter, 
    //     onFilterRemove, 
    //     isFilterOpen, 
    //     isMfgSelected,
    //     onAddFilter, 
    //     onApplyFilter, 
    //     toggleFilter
    // } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Proc_Day_Wise_Coverage);
    const { user } = useUserData();
    const reportName = "DayWiseCoverage";

    const themeUi = user?.user?.theme_ui;

    const getCalenderData = async () => {
        const data = await getData({ startDate: format(startOfMonth(startDate), "yyyy-MM-dd"), endDate: format(endOfMonth(endDate), "yyyy-MM-dd") });
        setCalenderData(data?.data?.data);
    }

    const dispatch = useDispatch()

    useEffect(() => {
        getCalenderData()
    }, [startDate, endDate]);

    const setDateRange = (start: string, end: string) => {
        setStartDate(start);
        setEndDate(end)
    }

    const getColor = (id: string) => {
        if (!calenderData?.[id]) {
            return Colors.NoData
        }
        if (id === selectedDate) {
            return Colors.Selected
        }
        return calenderData?.[id]?.oc === calenderData?.[id]?.fk ? Colors.Green : Colors.Red
    }

    const getToolTipContent = (id: string) => {
        if (!calenderData?.[id]) {
            return null
        }
        return (
            <table style={{ padding: "6px", display: "table", width: '150px',fontSize:"11px" }}>
                <thead>
                    <tr>
                        <td colSpan={2} style={{ borderBottom: "1px dashed white", paddingRight: "4rem" }}>Details</td>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>
                            No of Orders
                        </td>
                        <td>
                            {calenderData?.[id]?.oc}
                        </td>
                    </tr>
                    <tr>
                        <td>
                            Full kit
                        </td>
                        <td>
                            {calenderData?.[id]?.fk}
                        </td>
                    </tr>
                    <tr>
                        <td>
                            Partial kit
                        </td>
                        <td>
                            {calenderData?.[id]?.pk}
                        </td>
                    </tr>
                    <tr>
                        <td>
                            No kit
                        </td>
                        <td>
                            {calenderData?.[id]?.nk}
                        </td>
                    </tr>
                </tbody>

            </table>
        )
    }

    useEffect(() => {
        getAnalytics()
    }, [calenderData])

    useEffect(() => {
        setLoading(isCalenderLoading)
    }, [isCalenderLoading])

    const formatNumber = (number: number) => number % 1 !== 0 ? Math.round(number * 100) / 100 : number;

    const getAnalytics = () => {
        if (calenderData) {
            const analytics: any = {}
            const monthRange = eachMonthOfInterval({ start: startDate, end: endDate });
            monthRange.forEach((date: any) => {
                analytics[getMonth(date)] = {
                    green: 0,
                    red: 0
                }
            })
            Object.entries(calenderData).forEach((entry: any) => {
                const releasedDate = entry[0];
                // console.log(releasedDate,getColor(releasedDate) === Colors.Red)
                // const month = format(releasedDate, "MMM");
                const month = getMonth(releasedDate);
                const isGreen = getColor(releasedDate) === Colors.Green;
                let countOfGreen = analytics[month].green;
                let countOfRed = analytics[month].red;
                if (isGreen) {
                    countOfGreen += 1
                } else {
                    countOfRed += 1
                }
                analytics[month] = {
                    green: countOfGreen,
                    red: countOfRed
                }

            })


            const data = Object.entries(analytics).map((entry: any) => {
                const greens = entry[1].green;
                const reds = entry[1].red
                return [months[entry[0]], greens, reds, formatNumber((greens / (greens + reds) * 100) || 0)]
            })

            dispatch(DAYWISE_COVERAGE_ANALYTICS(data))
        }
    }

    const { renderView, toggleCurrentTab, date, currentTab,isMatReqDayWiseLoading,isMatReqLoading} = useMaterialReq(null, selectedDate);

    useEffect(() => {
        toggleCurrentTab({
            id: 'sdv',
            label: 'Selected Day View',
            value: 'sdv'
        })
       

    }, [selectedDate])

    useEffect(()=>{
        if(selectedDate && selectedDate.length && currentGridRef){
            setColumnDef();
        }
    },[selectedDate, currentGridRef])

    const colDefCustomizations = {
        ColorPriority: {
          cellRenderer: (params: any) => {
            if (params.node.group) {
              return null;
            }
            return ColorCellRenderer(params);
          },
        },
        Status: {
          hide: true,
          rowGroup: true,
        },
    };

    const setColumnDef = async () => {
        try {
          const response = await getUIConfigData(reportName);
          setColDef(getColumnDefinations(response.data.data, colDefCustomizations))
        }
        catch (e) {
          console.log(e);
        }
    }

    const getUserColumnConfig = async () => {
        try {
          const data = await getUserUIReportConfigData({
            un: user.user.name,
            rn_id: UIGridCode.ProcDayWiseCov
          });
    
          const newConfig = data?.data?.data[0]?.columns_settings ? JSON.parse(data?.data?.data[0]?.columns_settings) : [];
          setColumnState(newConfig);
    
          if (!data) {
            console.error('Failed to apply column state');
          }
        } catch (error) {
          console.error(error);
        }
    }
    
    useEffect(() => {
        if (colDef?.length && currentGridRef?.current) {
            
          setMasterUIConfig(currentGridRef?.current.api.getColumnState());
          
        }
      }, [colDef,currentGridRef]);

    useEffect(()=>{
        if(masterUIConfig && masterUIConfig.length){
            getUserColumnConfig();
        }
    },[masterUIConfig])


    const handleSaveClick = async (coldefs?:any) => {
        try {
          if (coldefs) {
            const payload = {
              un: user.user.name,
              rn_id: UIGridCode.ProcDayWiseCov,
              cs: JSON.stringify(coldefs),
            };
            await updateUserUIReportConfigData([payload]);
            setColumnState([...coldefs]);
            
          } 
          else {
              if (currentGridRef?.current?.api) {
                  const config = currentGridRef.current.api.getColumnState();
                  
                const payload = {
                  un: user.user.name,
                  rn_id: UIGridCode.ProcDayWiseCov,
                  cs: JSON.stringify(config)
                }
                await updateUserUIReportConfigData([payload]);
              } 
          }
        } catch (error) {
          console.error(error);
        }
      }

    const handleResetClick = () => {
        setIsReset(true);
    }

    useEffect(() => {
        if (isReset) {
          handleSaveClick(masterUIConfig);
          setIsReset(false);
        }
      }, [isReset]);

    const handleMaterialRequirementClick = ()=>{
        setShowModal(true);
    }

    // const getFilterData = async () => {
    // try {
    //     const response = await getPageWiseFilterData({page_name: FilterPageName.Proc_Day_Wise_Coverage});
    //     setFilterData(response?.data.data);
    // } catch (error) {
    //     console.error(error);
    // }
    // }


    const ExcelExport =()=>{
        currentGridRef?.current?.api?.exportDataAsExcel({ fileName: `Day_Wise_Coverage${format(Date.now(), "dd/MM/yyyy")}` })
      }

    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
            <div >
                <MTOActionToolBar 
                    isExcelExport 
                    themeUi={themeUi}
                    // isAddFilterButton
                    // isFilterOpen={isFilterOpen}
                    // onAddFilter={onAddFilter}
                    // toggleFilter={toggleFilter}
                    // onApplyFilter={onApplyFilter}
                    // multiFilter={currFilter}
                    // setMultiFilter={setCurrFilter}
                    // onFilterRemove={onFilterRemove}
                    // isMfgSelected={isMfgSelected}
                    onExcelExportClick={ExcelExport}
                    handleSaveClick={()=>handleSaveClick()}
                    handleResetClick={handleResetClick}
                />
            </div>
            <DayWiseCoverageHeader max={maxDate} min={minDate} startDate={startDate} endDate={endDate} setDateRange={setDateRange} />
            {(loading || isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />}
            <DayWiseCoverageCalender start={startDate} end={endDate} getToolTipContent={getToolTipContent} getColor={getColor} selectedDate={selectedDate} setSelectedDate={setSelectedDate} />
            <TableContainer>
                {calenderData?.[selectedDate] ?
                    <DayWiseCoverageTable
                        columnState={columnState}
                        setCurrentGridRef={setCurrentGridRef}
                        colDef={colDef}
                        currentGridRef={currentGridRef}
                        setLoading={setLoading}
                        startDate={format(startOfMonth(startDate), "yyyy-MM-dd")}
                        endDate={format(endOfMonth(endDate), "yyyy-MM-dd")}
                        selectedDate={selectedDate}
                    />
                    : <AnimationWrapper>
                        <Player src={'/assets/img/VectorFLOW/BPR/swipe pointer.json'} loop autoplay style={{ height: 100, width: 100 }} />
                        <HelperText>Please select the <strong>Dates</strong> from above to  view <strong>Order lists</strong></HelperText>
                    </AnimationWrapper>
                }
            </TableContainer>
            <VFModalCard openModal={showModal} closeModal={() => { setShowModal(false) }} headerText={'Material Coverage'} headerIcon={""} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"} paddingLeftAndRight={0} headerTextColor={'black'} backgroundColor={'f4f4f4'}>
                <div style={{position:'relative', margin: "2rem", overflow: "auto", width: "80vw", height: "70vh", display: "flex", flexDirection: "column" }}>
                    <MaterialRequirementComponent renderView={renderView} currentTab={currentTab} date={date} toggleCurrentTab={toggleCurrentTab} />
                {(isMatReqDayWiseLoading || isMatReqLoading) && <VFLoader/>}
                </div>
            </VFModalCard>
            {calenderData?.[selectedDate] && <div style={{ marginBottom: "1rem", marginTop: "-1rem", fontSize: "18px", fontWeight: "bold", cursor: "pointer", paddingTop: "1rem", display: 'flex', alignItems: 'center', gap: '1rem' }} onClick={handleMaterialRequirementClick}>Material Requirement <svg id="Layer_2" data-name="Layer 2" xmlns="http://www.w3.org/2000/svg" width="15.917" height="15.917" viewBox="0 0 15.917 15.917">
                <path id="Path_10654" data-name="Path 10654" d="M16.194,8.959a.724.724,0,0,0-.724.724v4.341a1.447,1.447,0,0,1-1.447,1.447H3.894a1.447,1.447,0,0,1-1.447-1.447V3.894A1.447,1.447,0,0,1,3.894,2.447H8.235A.724.724,0,0,0,8.235,1H3.894A2.894,2.894,0,0,0,1,3.894V14.023a2.894,2.894,0,0,0,2.894,2.894H14.023a2.894,2.894,0,0,0,2.894-2.894V9.682A.723.723,0,0,0,16.194,8.959Z" transform="translate(-1 -1)" fill="#b93b7e" />
                <path id="Path_10655" data-name="Path 10655" d="M19.9,1.444a.716.716,0,0,0-.135-.2c-.009-.009-.012-.022-.021-.031s-.022-.012-.031-.021A.679.679,0,0,0,19.235,1H14.894a.724.724,0,0,0,0,1.447h2.594L12.212,7.723a.723.723,0,1,0,1.023,1.023L18.512,3.47V6.064a.724.724,0,1,0,1.447,0V1.723a.716.716,0,0,0-.056-.279Z" transform="translate(-4.041 -1)" fill="#b93b7e" />
            </svg>
            </div>}
        </div>

    )
}

export default DayWiseCoverage