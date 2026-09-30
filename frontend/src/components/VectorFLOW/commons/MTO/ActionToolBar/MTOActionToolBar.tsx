import VFButton from '../../VFButton';
import {
    SCTaskBarContainer,
    SCGoBackContainer,
    SCGoBackText,
    SCVerticalDivider,
    SCVerticalDividerGray,
    SCCustomActionsContainer,
    SCViewContainerWithBg,
    SCTaskFilterContainer,
    SCButton,
    SCViewContainerWithBgToggle,
    SCHorizontalDivison,
    SCViewContainer,
    SCFilterVerticalDivider,
    /**search filter styles starts */
    VFSelectedFiltersChip,
    VFSelectedFiltersFilterCloseIcon,
    VFSelectedFiltersFilterContent,
    VFSelectedFiltersFilterLabel,
    VFSelectedFiltersFilterValue,
    VFSelectedFiltersPlaceHolder,
    VFSelectedFiltersWrapper,
    VFFilterScrollBar,
    /**search filter styles end*/
    /**Date component style starts */
    DateWrapper,
    DateIcon,
    DateTitle,
    DateValue,
    VFSelectedFilterLabel,
    AddFilterWrapper
} from './styles';
import moment from 'moment';
import { ReactElement } from 'react';
import { format } from 'date-fns';
import VFCommonFilter from '../../../../../VectorFlow/Pages/MTO/Common/VFCommonFilter';
import { getSelectedFilters } from '../../../../../helpers/utils';
import { ExportExcelSVG, ResetSVG, SaveSVG,GridView,ChartView } from '../../../../../helpers/SvgRenderer';
import { Theme } from '../../../../../styles/global';
import VFDatePicker from '../../../../../VectorFlow/Pages/MTO/Common/VFDatePicker';
import {textComparators, numberComparators} from '../../../../../VectorFlow/Pages/MTO/Common/VFCommonFilter/InputTypes'

type filterType = {
    label: string,
    values: string[]
}


interface MTOActionToolBarProps {
    comp?: string,
    onDateChange?: (date: string) => void;
    submitDate?: () => void;
    isGridView?: boolean;
    setIsGridView?: (isGridView: boolean) => void;
    onAddFilter?: () => void;
    selectedFilters?: filterType[];
    removeFilters?: (category: string, name: string) => void;
    disableRemoveFilter?: boolean | undefined;
    date?: string
    handleGoBack?: () => void;
    themeUi?: Theme | any;
    quickFilter?: ReactElement | null
    WIPFilter?: ReactElement | null

    //// new props
    isGoBackButton?: boolean
    isReleaseDate?: boolean
    isAsOnDate?: boolean
    isAddFilterButton?: boolean
    isExcelExport?: boolean
    isChartGridToggle?: boolean
    isWIPCheckBox?: boolean
    isFilterOpen?: boolean
    toggleFilter?: (state: boolean) => void
    multiFilter?: any
    setMultiFilter?: any
    onApplyFilter?: (params: any) => void;
    onFilterRemove?: any;
    isMfgSelected?: boolean;
    utilityBtns?: ReactElement | null,
    handleSaveClick?: () => void
    handleResetClick?: () => void
    onExcelExportClick?: () => void
    ReleaseOrderHeader?: ReactElement | null;
    saveBtnName?:string;
    resetBtnName?:string;
    //// new props
}

 

const MTOActionToolBar = ({
    onDateChange,
    isGridView = true,
    setIsGridView,
    onAddFilter,
    selectedFilters,
    removeFilters,
    disableRemoveFilter,
    isMfgSelected,
    themeUi,
    submitDate,
    date,
    handleGoBack,
    isGoBackButton,
    isReleaseDate,
    isAsOnDate,
    isAddFilterButton,
    isExcelExport,
    isChartGridToggle,
    // isWIPCheckBox,
    isFilterOpen,
    toggleFilter,
    multiFilter,
    setMultiFilter,
    onApplyFilter,
    onFilterRemove,
    quickFilter,
    utilityBtns,
    WIPFilter,
    handleSaveClick,
    handleResetClick,
    onExcelExportClick,
    ReleaseOrderHeader,
    saveBtnName,
    resetBtnName,
}: MTOActionToolBarProps) => {

    const handleRemoveFilter = (category: string, name: string) => {
        if (removeFilters) {
            removeFilters(category, name);
        }
    }


    const format2 = "yyyy-MM-dd";
    
    const newFilters = getSelectedFilters(multiFilter, isMfgSelected);



    return (
        <SCTaskBarContainer className='toolbar-container'>
            <SCTaskFilterContainer
                style={{
                    maxWidth: '50%',
                    width: 'unset',
                    justifyContent: 'unset'
                }}>
                <>
                    {ReleaseOrderHeader &&
                        <div>
                            {ReleaseOrderHeader}
                        </div>
                    }
                </>
                <>
                    {isGoBackButton &&

                        <SCGoBackContainer onClick={() => { if (handleGoBack) handleGoBack() }}>
                            <img
                                src="/assets/img/VectorFLOW/BPR/goback.svg"
                                alt=""
                            />
                            <SCGoBackText ><b>Go Back</b></SCGoBackText>
                        </SCGoBackContainer>
                    }

                    {quickFilter && <div style={{ display: "flex", justifyContent: "center", alignItems: "center", fontSize: "1.8rem", minWidth: "max-content" }}>
                        {quickFilter}
                    </div>}

                    {/* {isWIPCheckBox &&
                        <CheckBoxDiv data-testid='check-box'>
                            <Checkbox
                                data-testid='check-box'
                                name="select"
                                value="1"
                                defaultChecked={true}
                                //type="checkbox"
                                onChange={() => console.log('hi')}
                            //style={{ display: 'inline' }}
                            />
                            <InputCheckBoxTitle>Show order with available WIP Only</InputCheckBoxTitle>
                        </CheckBoxDiv>
                    } */}


            {isReleaseDate &&
              <div
                data-testid='isReleaseDate'
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginRight: '3px',
                  fontSize: '18px',
                  fontWeight: 'bold',
                  width: '100%'
                }}>

                &nbsp;
                <p>Release Date Till</p>
                &nbsp;
                &nbsp;
                <VFDatePicker  
                    date={date ? new Date(date) : null} 
                    onDateChange={onDateChange} 
                    dateInputStyle = {{fontSize:"18px",fontWeight:"bold"}}
                    imgStyle={{height:'25px', width:'25px'}}
                    showCalendarIcon={true}
                />
                            
                &nbsp;
                {/* <div style={{ display: 'flex', alignItems: 'center' }}>
                                <img
                                    style={{ cursor: 'pointer' }}
                                    src={themeUi === "REGALBLAZE" ? "/assets/img/Group 627-regal.svg" : "/assets/img/Group 627.svg"}
                                    height={50}
                                    width={60}
                                    alt="Group 627"
                                    onClick={() => { if (submitDate) submitDate() }}
                                />

                            </div> */}
                <VFButton
                  data-testid={"Group 627"}
                  onClick={() => submitDate && submitDate()}
                  themeUi={themeUi}
                  disabled={false}
                  style={{
                    height: "45px",
                    width: "60px",
                    borderRadius: "3px",
                  }}
                >
                  <img
                    src="/assets/img/rightArrowHorizontal.svg"
                    height={13}
                    width={7}
                  />
                </VFButton>

              </div>

            }

                    {/* <SCVerticalDivider /> */}
                </>

                {isAsOnDate &&
                    <DateWrapper data-testid='isAsOnDate'>
                        <DateIcon
                            src='/assets/img/calender-icon.svg' alt='calender-icon'
                        />
                        <DateTitle>As on Date</DateTitle>
                        <DateValue>
                            {format(new Date(), format2)}
                        </DateValue>
                    </DateWrapper>}
                {/**Temp Enquiry response Filter start */}
                {selectedFilters && selectedFilters?.length > 0 && <VFSelectedFiltersWrapper style={{ width: '700px' }}>
                    <VFSelectedFiltersPlaceHolder>
                        Selected Filters
                    </VFSelectedFiltersPlaceHolder>
                    <VFFilterScrollBar >
                        {
                            selectedFilters?.map((filter: filterType) => {
                                if (filter.values.length > 0) {
                                    return (
                                        <VFSelectedFiltersChip key={filter.label}>
                                            <VFSelectedFiltersFilterLabel>
                                                {filter?.label}:
                                            </VFSelectedFiltersFilterLabel>
                                            {filter?.values?.map((value: string) => (
                                                <div key={value}>
                                                    <VFSelectedFiltersFilterContent>
                                                        <VFSelectedFiltersFilterValue>
                                                            <p style={{ margin: '0px 5px 0px 5px' }}> {value}</p>
                                                        </VFSelectedFiltersFilterValue>
                                                        {<VFSelectedFiltersFilterCloseIcon
                                                            onClick={() => handleRemoveFilter(filter?.label, value)}
                                                            src='/assets/img/VectorFLOW/BPR/close-circle.svg' alt='close-icon' data-testid={'closeIcon-filter'}
                                                        />}
                                                        {filter?.values?.length > 1 && <SCFilterVerticalDivider />}
                                                    </VFSelectedFiltersFilterContent>
                                                </div>
                                            )
                                            )}
                                        </VFSelectedFiltersChip>
                                    )
                                }
                            })
                        }
                    </VFFilterScrollBar>
                </VFSelectedFiltersWrapper>}
                {/**Selected Filter ends*/}

                {
                    WIPFilter &&
                    <div>
                        {WIPFilter}
                    </div>
                }

            </SCTaskFilterContainer>
            {/**New Selected Filter start */}
            {isAddFilterButton && newFilters && Object.keys(newFilters)?.length > 0 &&
                <VFSelectedFiltersWrapper>
                 <VFSelectedFiltersPlaceHolder>
                    Selected Filters
                </VFSelectedFiltersPlaceHolder>

                <VFFilterScrollBar>
                {
                    Object.keys(newFilters)?.map((key: any) => (
                        <VFSelectedFiltersChip key={key}>
                        <VFSelectedFiltersFilterLabel>
                            {newFilters[key]?.name} <SCFilterVerticalDivider />
                            </VFSelectedFiltersFilterLabel>
                            
                            {newFilters[key]?.filters?.map((filter: any, index: number) => {
                                const operatorText = filter?.operator && filter?.operator !== '' ? (
                                    filter?.type === 'textCompare' ? textComparators?.find((item: any) => item.value === filter?.operator)?.label + ' ' 
                                    : filter?.type === 'numberCompare' ? numberComparators?.find((item: any) => item.value === filter?.operator)?.label + ' '
                                        : '') 
                                    : '';
                                            
                            return (
                        (filter?.value?.length > 0) &&
                        <>
                            <VFSelectedFilterLabel>
                            {filter?.label}:
                            </VFSelectedFilterLabel>

                            {filter?.value?.map((f: any) => {
                            return (
                                <div key={f.value}>
                                <VFSelectedFiltersFilterContent>
                                    <VFSelectedFiltersFilterValue>         
                                    <p style={{ margin: '0px 5px 0px 5px', fontFamily: '500' }}> 
                                        { operatorText ? operatorText :''}{f.label || f.value}
                                    </p>
                                    </VFSelectedFiltersFilterValue>

                                    {disableRemoveFilter ? (
                                    <div>-</div>
                                    ) : (
                                    <VFSelectedFiltersFilterCloseIcon
                                        onClick={() => {
                                        const filtervalue = f.id || f.value;
                                        onFilterRemove(key, filter.filterId, filtervalue);
                                        }}
                                        src='/assets/img/VectorFLOW/BPR/close-circle.svg'
                                        alt='close-icon'
                                        data-testid={'closeIcon-filter'}
                                    />
                                    )}
                                </VFSelectedFiltersFilterContent>
                                </div>
                            );
                            })}

                            {index !== newFilters[key]?.filters?.length - 1 && <SCFilterVerticalDivider />}
                        </>
                     );
                    })}
                </VFSelectedFiltersChip>
                ))
                }
                </VFFilterScrollBar>
                </VFSelectedFiltersWrapper>
                 }
            {/**Selected Filter ends*/}
        

            <SCCustomActionsContainer>
                {utilityBtns && <div style={{ display: "flex", justifyContent: "center", alignItems: "center", fontSize: "1.8rem", gap: "1.5rem", marginRight: "10px" }}>
                    {utilityBtns}
                </div>}
               
                    {isAddFilterButton && (
                        onAddFilter ? (
                            <AddFilterWrapper>
                            <VFButton
                                onClick={() => onAddFilter()}
                                themeUi={themeUi}
                                disabled={false}
                                width={110}
                            >
                                {(selectedFilters || newFilters) &&
                                (selectedFilters?.length || Object.keys(newFilters).length) ? (
                                <p style={{ padding: "2px" }}>Edit Filter</p>
                                ) : (
                                <p style={{ padding: "2px" }}>+ Add Filter</p>
                                )}
                            </VFButton>
                            </AddFilterWrapper>
                        ) : (
                            <AddFilterWrapper>
                            <SCButton>
                                <p>+ Add Filter</p>
                            </SCButton>
                            </AddFilterWrapper>
                        )
                 )}

                <>
                    {isExcelExport && <>
                        <SCVerticalDivider  />
                        <SCViewContainerWithBg onClick={onExcelExportClick}
                         >
                            <>
                               
                                <ExportExcelSVG theme={themeUi}/>
                                <p style={{padding:"5px"}}>Excel Export</p>
                            </>
                        </SCViewContainerWithBg>
                    </>}

                    {isGridView && handleSaveClick && handleResetClick && <>
                        <SCVerticalDividerGray />
                        <SCViewContainerWithBg onClick={() => handleSaveClick()}>
                           

                            <SaveSVG theme={themeUi}/>

                            <p style={{padding:"5px"}}>{saveBtnName ?? "Save Layout"}</p>
                        </SCViewContainerWithBg>
                        <SCViewContainerWithBg onClick={() => handleResetClick()}>
                            <ResetSVG theme={themeUi}/>
                            <p style={{padding:"5px"}}>{resetBtnName ?? "Reset Layout"}</p>
                        </SCViewContainerWithBg>
                    </>}

                    {/* Toggle button for chartview/ grid view */}
                    {isChartGridToggle &&
                        <>
                        {isAddFilterButton && <SCVerticalDividerGray />}
                            <SCViewContainerWithBgToggle >
                                <SCViewContainer onClick={() => { isGridView && setIsGridView && (setIsGridView(!isGridView)) }}>

                                <ChartView theme={themeUi} view={!isGridView}/>
                                    <p>Chart View</p>

                                </SCViewContainer>

                                <SCHorizontalDivison />

                                <SCViewContainer onClick={() => { !isGridView && setIsGridView && (setIsGridView(!isGridView)) }} style={{paddingTop:'7px'}}>
                                    <GridView theme={themeUi} view={isGridView}/>
                                    <p>Grid View</p>

                                </SCViewContainer>

                            </SCViewContainerWithBgToggle>
                        </>
                    }

                </>
                {isFilterOpen && toggleFilter && onApplyFilter && setMultiFilter && multiFilter &&
                    <VFCommonFilter
                        onApplyFilter={onApplyFilter}
                        onGoBack={() => toggleFilter(false)}
                        multiFilter={multiFilter}
                        setMultiFilter={setMultiFilter}
                    isFilterOpen={isFilterOpen}
                    />
                }

            </SCCustomActionsContainer >
        </SCTaskBarContainer >
    )
}

export default MTOActionToolBar