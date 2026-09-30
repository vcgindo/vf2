import { useEffect, useRef, useState } from "react";
import FilterModal from "./FilterModal";
import Note from "./Note";
import ResizableTable from "./ResizableTable";
import MTOActionToolBar from "../../../../../../src/components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import {
  BlurCover,
  BTRAllomentSection,
  BTRTableWrapper,
  CardCover,
  DashedCard,
  EnquiryWrapper,
  EstimatedWrapper,
  // FilterWrapper,
  MessageText,
  RmUICont,
  TabSwitchContainer,
  TabSwitchHeading,
  TabsWrapper,
} from "./styles";
// import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard";
// import { FilterAccordianWrapper, FilterContainer, FilterHeading, HorizontalLine, PlantInput, SearchBar } from "./FilterModal/styles";
// import FilterAccordian from "./FilterAccordian";
import { useGetEnquiryResData } from "../../../../Services/MTO/Production/EnquiryResponse";
import { useUserData } from "../../../../../context/index";
import { notifyError, notifyLoader } from "../../../../../helpers/notify";
import { toast } from "react-toastify"
import VFCapsule from "../../../../../components/VectorFLOW/commons/VFCapsule";
import { Allotment } from "allotment";
import useViewPort from "../../../../../hooks/useViewPort";
import { useGetUIConfigData } from "../../../../../VectorFlow/Services/MTO/Common/UIConfig";
import { getColumnDefinations } from "../../../../../helpers/utils";
import FullkitCellRenderer from "../../Common/FullKitCellRenderer/FullkitCellRenderer";
import { UIGridCode } from "../../Common/Enum";
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import OverlayLoader from "../../Common/Loader";
import { format } from "date-fns";
import { ExcelExportName } from "../../Common/Enum";
const tabOptions = [{ label: "RM Not Available", value: "RM Not Available" }, { label: "RM Available", value: "RM Available" }];


const EnquiryResponse = () => {
  const [activeTab, setActiveTab] = useState<number>(0);
  const [activeCapsule, setActiveCapsule] = useState<{ label: string, value: string }>(tabOptions[0]);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [tableData, setTableData] = useState<any>([]);
  const [filterData, setFilterData] = useState<any>([]);
  const [selectedFilters, setSelectedFilters] = useState<any>([]);
  const [hasProductGroup, setHasProductGroup] = useState<any>(false);
  const [currentGridRef, setCurrentGridRef] = useState<any>(null);
  const [columnState, setColumnState] = useState<any>([]);
  const [isReset, setIsReset] = useState<any>(undefined);
  const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
  const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
  const { data } = useGetEnquiryResData() || {};
  const [masterUIConfig, setMasterUIConfig] = useState([]);
  const { screenHeight } = useViewPort()

  const [HeaderData, setHeaderData] = useState([]);
  const { mutateAsync: getUIConfigData } = useGetUIConfigData()

  const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
  const [userPageSize, setUserPageSize] = useState<any>();
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [totalRow, setTotalRow] = useState<number>(0)

  const reportName = "EnquiryResponse";
  const [myColDefs, setMyColDefs] = useState([{}]);
  const gridRef = useRef<any>();

  const setColumnDef = async () => {          //intial column names and set kr rha hai in headerData
    try {
      const response = await getUIConfigData(reportName);
      setHeaderData(response.data.data);
    }
    catch (e) {
      console.log(e);
    }
  }

  const [selectedOptions, setSelectedOptions] = useState<any>({
    plantName: "",
    productGroup: [],
    department: {},
    ccrGroup: {},
    ccrName: {},
  });
  const { user } = useUserData();
  // const {state:multiFilter,setState:setMultiFilter,onDelete} = useBPRFilter()
  const themeUi = user.user.theme_ui;

  const handleTabChange = (tab: any) => {
    if (tab?.label === 'RM Not Available') {
      setActiveTab(0);
    } else {
      setActiveTab(1);
    }
    setActiveCapsule(tab);
  };

  const getTableSimData = (filterData: any): any => {
    const bufferData = filterData.length > 0 ? filterData : [];

    const simData: any = [];

    for (let index = 0; index < bufferData.length; index++) {
      const element = bufferData[index];
      let existIndex: any = -1;

      for (let i = 0; i < simData.length; i++) {
        if (simData[i].plnm === element.plnm) {
          existIndex = i;
          break; // Found the matching element, no need to continue the loop
        }
      }

      if (existIndex !== -1) {
        simData[existIndex] = {
          ...simData[existIndex],
          cnm: ((element.fol <= simData[existIndex].fol) ? element.cnm : simData[existIndex].cnm),
          fol: Math.min(simData[existIndex].fol, element.fol),
        };
      } else {
        simData.push({ ...element }); // Clone the object to avoid mutation
      }
    }

    return simData;
  };

  function getWeekOfMonth(dateString: string): string {
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];

    // Parse the input date string
    const [dayStr, monthStr, yearStr] = dateString.split(' ');
    const day = parseInt(dayStr, 10);
    const monthIndex = months.findIndex(
      (m) => m.toLowerCase() === monthStr.toLowerCase()
    );
    const year = parseInt(yearStr, 10);

    // Create a Date object
    const date = new Date(year, monthIndex, day);

    // Get the day of the month and calculate the week number
    const dayOfMonth = date.getDate();
    const startOfMonth = new Date(year, monthIndex, 1);
    const startOfMonthDay = startOfMonth.getDay();
    const weekOfMonth = Math.ceil((dayOfMonth + startOfMonthDay) / 7);

    // Format output
    const month = months[monthIndex];
    const weekString = `${month}-week ${weekOfMonth}`;

    return weekString;
  }

  const getFormattedDate = (date: any) => {
    const day = date.getDate();
    const month = date.toLocaleString("default", { month: "short" });
    const year = date.getFullYear();

    return getWeekOfMonth(`${day} ${month} ${year}`);
  };

  const getEarliestDate = (array: number[]) => {

    const today = new Date();
    const result = new Date(today);
    let daysToAdd = 0;

    for (let index = 0; index < array.length; index++) {
      daysToAdd = daysToAdd + array[index];

    }

    return getFormattedDate(
      new Date(result.setDate(today.getDate() + daysToAdd))
    );
  };

  const getRMUI = () => {
    if (filterData) {

      const simData = getTableSimData(filterData);

      return (
        <RmUICont style={{ background: 'white' }}>

          <table style={{ margin: '10px 0', borderSpacing: '0', fontFamily: 'Roboto' }}>
            <thead style={{ marginBottom: '20px', textAlign: 'center' }}>
              <tr style={{ rowGap: '2px' }}>
                <td style={{ borderRight: '1px solid grey', borderBottom: '5px solid white', paddingLeft: '16px' }}>Plant</td>
                {(!activeTab) &&

                  <td style={{ borderRight: '1px solid grey', borderBottom: '5px solid white', paddingLeft: '6px' }}>Procurement Buffer</td>

                }
                <td style={{ borderRight: '1px solid grey', borderBottom: '5px solid white', paddingLeft: '6px' }}>Production Buffer</td>
                <td style={{ borderRight: '1px solid grey', borderBottom: '5px solid white', paddingLeft: '6px' }}>Least Loaded CCR</td>

                <td style={{ paddingLeft: '6px', borderBottom: '5px solid white' }}>Earliest Readiness Date</td>
              </tr>
            </thead>
            <tbody>


              {simData.map((row: any, index: any) => (
                (row.it[selectedOptions.productGroup[0]]) &&

                <tr style={{ background: `${(((index % 2 === 0))) ? '#F8F8F8' : 'white'}` }} key={index}>
                  <td style={{ padding: '5px', paddingLeft: '16px', textAlign: 'center' }}>{row.plnm}</td>
                  {
                    (!activeTab) &&
                    <td style={{ paddingLeft: '4px', textAlign: 'center', paddingRight: '20px' }}>{row.it[selectedOptions.productGroup[0]]?.proc_size} &nbsp; days</td>

                  }
                  <td style={{ paddingLeft: '4px', textAlign: 'center', paddingRight: '20px' }} >{row.it[selectedOptions.productGroup[0]]?.prod_size}&nbsp; days</td>
                  <td style={{ paddingLeft: '4px', textAlign: 'center' }} >{row.cnm}</td>
                  {
                    (!activeTab) ?

                      <td style={{ color: '#BC3D81', paddingLeft: '6px', textAlign: 'center', fontWeight: 'bold' }} >{getEarliestDate([row.fol, row.it[selectedOptions.productGroup[0]]?.proc_size, row.it[selectedOptions.productGroup[0]]?.prod_size])}</td>
                      :
                      <td style={{ color: '#BC3D81', paddingLeft: '6px', textAlign: 'center', fontWeight: 'bold' }} >{getEarliestDate([row.fol, row.it[selectedOptions.productGroup[0]]?.prod_size])}</td>
                  }
                </tr>

              ))}

            </tbody>
          </table>
        </RmUICont>
      );
    }
    return (
      <></>
    )
  };

  const handleNameChange = (arr: any) => {
    setSelectedOptions((prev: any) => ({ ...prev, plantName: arr }));
  };

  const handleFilterSelect = (event: any, category: string, index: number) => {
    const { name, checked } = event.target;

    if (category === "Product Group") {
      const prodGrp = selectedOptions?.productGroup;
      if (checked) {
        prodGrp[0] = name;
      } else {
        prodGrp?.splice(index, 1);
      }
      setSelectedOptions((prev: any) => ({
        ...prev,
        productGroup: [...prodGrp],
      }));
    }

    if (category === "Department") {
      const dept = selectedOptions?.department;
      if (checked && !dept[name]) {
        dept[name] = checked;
      } else {
        delete dept[name];
      }
      setSelectedOptions((prev: any) => ({ ...prev, department: { ...dept } }));
    }

    if (category === "CCR Group") {
      const ccrGrp = selectedOptions?.ccrGroup;
      if (checked && !ccrGrp[name]) {
        ccrGrp[name] = checked;
      } else {
        delete ccrGrp[name];
      }
      setSelectedOptions((prev: any) => ({ ...prev, ccrGroup: { ...ccrGrp } }));
    }

    if (category === "CCR") {
      const ccrNm = selectedOptions?.ccrName;
      if (checked && !ccrNm[name]) {
        ccrNm[name] = checked;
      } else {
        delete ccrNm[name];
      }
      setSelectedOptions((prev: any) => ({ ...prev, ccrName: { ...ccrNm } }));
    }
  };

  const handleModalToggle = () => {
    setIsModalOpen(!isModalOpen);
  };

  const filterByPlNames = (names: any[]) => {
    if (names.length === 0) {
      return tableData;
    }
    const data = [];
    for (let i = 0; i < tableData?.length; i++) {
      const current = tableData[i];
      for (let j = 0; j < names.length; j++) {
        if (current?.plnm?.includes(names[j].name)) {
          data?.push(current);
          break; // If a match is found, break out of the inner loop
        }
      }
    }
    return data;
  };

  const filterByProdGrpName = (data: any, productGrp: any) => {
    const updatedData = [];
    for (let i = 0; i < data?.length; i++) {
      const current = data[i];
      if (Object.keys(current?.it).includes(productGrp[0])) {
        updatedData?.push(current);
      }
    }
    return updatedData;
  };

  const filterByDeptName = (data: any, department: any) => {
    const updatedData = [];
    for (let i = 0; i < data?.length; i++) {
      const current = data[i];
      if (department[current?.dpnm]) {
        updatedData?.push(current);
      }
    }
    return updatedData;
  };
  const filterByccrGroupName = (data: any, ccrGrpName: any) => {
    const updatedData = [];
    for (let i = 0; i < data?.length; i++) {
      const current = data[i];
      if (ccrGrpName[current?.gnm]) {
        updatedData?.push(current);
      }
    }
    return updatedData;
  };
  const filterByccrName = (data: any, ccrName: any) => {
    const updatedData = [];
    for (let i = 0; i < data?.length; i++) {
      const current = data[i];
      if (ccrName[current?.cnm]) {
        updatedData?.push(current);
      }
    }
    return updatedData;
  };

  const updatedSelectedFilters = (options: any) => {
    const filters: { label: string; values: string[] }[] = [];


    if (options?.plantName) {
      const names = options.plantName.map((plantName:any)=>plantName.name)
      filters.push({
        label: "Plant",
        values: [...names],
      });
      
    }
    if (options?.productGroup?.length > 0) {
      filters.push({
        label: "Product Group",
        values: [...options.productGroup],
      });
    }
    if (Object.keys(options?.department)?.length > 0) {
      filters.push({
        label: "Department",
        values: [...Object.keys(options?.department)],
      });
    }
    if (Object.keys(options?.ccrGroup)?.length > 0) {
      filters.push({
        label: "CCR Group",
        values: [...Object.keys(options?.ccrGroup)],
      });
    }
    if (Object.keys(options?.ccrName)?.length > 0) {
      filters.push({
        label: "CCR Name",
        values: [...Object.keys(options?.ccrName)],
      });
    }

    setSelectedFilters(filters);
  }

  const applyFilter = (options: any) => {
    let data = [];
    data = filterByPlNames(options?.plantName);
    data =
      options?.productGroup?.length > 0
        ? filterByProdGrpName(data, options?.productGroup)
        : data;
    data =
      Object.keys(options?.department)?.length > 0
        ? filterByDeptName(data, options?.department)
        : data;
    data =
      Object.keys(options?.ccrGroup)?.length > 0
        ? filterByccrGroupName(data, options?.ccrGroup)
        : data;
    data =
      Object.keys(options?.ccrName)?.length > 0
        ? filterByccrName(data, options?.ccrName)
        : data;

    updatedSelectedFilters(options);
    setHasProductGroup(options?.productGroup?.length > 0);
    setFilterData(data);
    setIsModalOpen(false);
  };

  const message = (
    <p>
      The Readiness date is valid for order booked today. This can change if
      there are delays in order booking.
      <br />
      For large orders please contact planning team.
    </p>
  );

  const productGroupOptions: any = [];
  const departmentOptions: any = [];
  const ccrGroupOptions: any = [];
  const ccrNameOptions: any = [];
  const plantOptions: any = []

  function getUniqueValues<T extends Record<any, any>>(array: T[], key: any): T[] {
    const uniqueArray: T[] = [];
    const uniqueValues: any[] = [];

    for (const item of array) {
      if (!uniqueValues.includes(item[key])) {
        uniqueValues.push(item[key]);
        uniqueArray.push(item);
      }
    }
    return uniqueArray;
  }

  for (let i = 0; i < tableData?.length; i++) {
    const ccrObj = tableData[i];
    if (ccrObj?.plnm) {
      plantOptions.push({ value: ccrObj.plnm, label: ccrObj.plnm, name: ccrObj.plnm });
      // plantOptions = getUniqueValues(plantOptions)
    }
    if (ccrObj?.it) {
      const types = Object.keys(ccrObj?.it);
      for (let j = 0; j < types.length; j++) {
        if (!productGroupOptions?.includes(types[j])) {
          productGroupOptions.push(types[j]);
        }
      }
    }

    if (ccrObj?.dpnm) {
      if (!departmentOptions?.includes(ccrObj?.dpnm)) {
        departmentOptions.push(ccrObj?.dpnm);
      }
    }

    if (ccrObj?.gnm) {
      if (!ccrGroupOptions?.includes(ccrObj?.gnm)) {
        ccrGroupOptions.push(ccrObj?.gnm);
      }
    }

    if (ccrObj?.cnm) {
      if (!ccrNameOptions?.includes(ccrObj?.cnm)) {
        ccrNameOptions.push(ccrObj?.cnm);
      }
    }
  }

  const filters = [
    {
      key: "plnm",
      heading: "Plant",
      options: getUniqueValues(plantOptions, 'value')
    },
    {
      key: 'prdGrp',
      heading: "Product Group",
      options: productGroupOptions,
    },
    {
      key: 'dept',
      heading: "Department",
      options: departmentOptions,
    },
    {
      key: 'ccrGrp',
      heading: "CCR Group",
      options: ccrGroupOptions,
    },
    {
      key: 'ccrNm',
      heading: "CCR",
      options: ccrNameOptions,
    },
  ];

  const removeFilters = (category: string, name: string) => {


    const updtedCCRName = selectedOptions?.ccrName;
    const updtedDept = selectedOptions?.department;
    const updtedCCRGrp = selectedOptions?.ccrGroup;
    let updatedPlantName = selectedOptions?.plantName;
    let updatedProductGrp = selectedOptions?.productGroup;

    if (category === "Plant") {
      updatedPlantName = updatedPlantName.filter((item: any) => item.name !== name);
      if (updatedPlantName.length === 0) {

        updatedPlantName = "";

        setSelectedOptions((prev: any) => ({
          ...prev,
          plantName: updatedPlantName
        }));
      }
      else {
        setSelectedOptions((prev: any) => ({
          ...prev,
          plantName: updatedPlantName
        }));
      }

    }
    if (category === "Product Group") {
      updatedProductGrp = [];
      setSelectedOptions((prev: any) => ({
        ...prev,
        productGroup: updatedProductGrp,
      }));
    }
    if (category === "Department") {
      delete updtedDept[name];
      setSelectedOptions((prev: any) => ({
        ...prev,
        department: updtedDept,
      }));
    }
    if (category === "CCR Group") {
      delete updtedCCRGrp[name];
      setSelectedOptions((prev: any) => ({
        ...prev,
        ccrGroup: updtedCCRGrp
      }));
    }
    if (category === "CCR Name") {
      delete updtedCCRName[name];
      setSelectedOptions((prev: any) => ({
        ...prev,
        ccrName: updtedCCRName,
      }));
    }
    updatedSelectedFilters({
      plantName: updatedPlantName,
      productGroup: updatedProductGrp,
      department: updtedDept,
      ccrGroup: updtedCCRGrp,
      ccrName: updtedCCRName
    });
    applyFilter({
      plantName: updatedPlantName,
      productGroup: updatedProductGrp,
      department: updtedDept,
      ccrGroup: updtedCCRGrp,
      ccrName: updtedCCRName
    });
  };
  
  const getData = (data: any) => {
    try {
          setTableData(data?.data?.data);
          setTotalRow(data?.data?.data.length);
        } catch (e) {
          console.log(e);
          notifyError('Failed to set Enquiry data!');
        }
    
  }

  const savePageSize = (pageSize: any) => {
      if (pageSize) {
        setUserPageSize(pageSize);
          setCurrentPage(1)
          handleSaveClick(undefined, pageSize);
        } else {
          notifyError("Invalide page size");
      }
      
  }
  const getUserColumnConfig = async () => {   
    try {
      const data = await getUserUIReportConfigData({
        un: user.user.name,
        rn_id: UIGridCode.ProdEnquiryResponse
      });

      setUserConfigFetched(true)
      const newConfig = JSON.parse(data?.data?.data[0]?.columns_settings) || [];
      setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : undefined);
      setColumnState(newConfig.cs);
      if (!data) {
        console.error('Failed to apply column state');
      }
    } catch (error) {
      console.error(error);
    }
  }

  const handleSaveClick = async (coldefs?: any, page_size?: any) => {
    try {
      if (coldefs) {
        const fullConfig = { cs: coldefs, pageSize: userPageSize };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdEnquiryResponse,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIReportConfigData([payload]);
        setColumnState([...coldefs]);
        
      } else if (page_size) {
        const fullConfig = { cs: columnState, pageSize: page_size };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdEnquiryResponse,
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
            rn_id: UIGridCode.ProdEnquiryResponse,
            cs: JSON.stringify(fullConfig)
          }
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

  useEffect(() => {
    if (isReset) {
      handleSaveClick(masterUIConfig);
      setIsReset(false);
    }
  }, [isReset]);

  useEffect(() => {
    if (currentGridRef?.current) {
      setMasterUIConfig(currentGridRef?.current.api.getColumnState());
    }
  }, [myColDefs]);

  useEffect(() => {
    notifyLoader("Loading Grid Data")
    if (data?.data?.data  && userConfigFetched) {
      setCurrentPage(1);
      setTableData(data?.data?.data);
    }
    toast.dismiss()
  }, [data, userConfigFetched]);

  useEffect(() => {
    setFilterData(data?.data?.data);
  }, [tableData]);

  useEffect(() => {
    setColumnDef();
  }, [])

  const CustomHeader = {
    'FOL(inDays)': {
      cellRenderer: FullkitCellRenderer
    }
  }

  useEffect(() => {
    if (HeaderData.length > 0) {
      setMyColDefs(getColumnDefinations(HeaderData, CustomHeader));
      getUserColumnConfig();
    }
  }, [HeaderData])

 
    
  const ExcelExport =()=>{
    const exportName = ExcelExportName.Enquiry_Response
    gridRef.current?.api?.exportDataAsExcel({ fileName: exportName,sheetName: exportName })
  }
  return (
    <EnquiryWrapper>
      {(isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />}
      
        <MTOActionToolBar
          comp={"EnquiryResponse"}
          isAddFilterButton
          isAsOnDate
          isExcelExport
          onExcelExportClick={ExcelExport}
          onAddFilter={handleModalToggle}
          selectedFilters={selectedFilters}
          removeFilters={removeFilters}
          themeUi={themeUi}
          handleSaveClick={handleSaveClick}
          handleResetClick={handleResetClick}
        />
      
      <div style={{ paddingLeft: '25px' }}>
        <BTRTableWrapper style={{ height: screenHeight - 145, margin: '0' }}>
          <Allotment vertical separator   >
            <Allotment.Pane preferredSize={'55%'}>
              <BTRAllomentSection>
                <ResizableTable 
                  gridRef={gridRef}
                  colDef={myColDefs} 
                  data={filterData}
                  setCurrentGridRef={setCurrentGridRef}
                  currentGridRef={currentGridRef}
                  columnState={columnState}
                  savePageSize={savePageSize}
                  userPageSize={userPageSize}

                />
              </BTRAllomentSection>
            </Allotment.Pane>
            <Allotment.Pane preferredSize={'45%'}>
              <BTRAllomentSection style={{ paddingTop: '10px' }}>
                <EstimatedWrapper>
                  <div
                    style={{ WebkitFilter: `blur(${hasProductGroup ? "0px" : "3px"})`, padding: "20px 25px" }}
                  >
                    <TabSwitchContainer>
                      <TabSwitchHeading>Estimated Due Date</TabSwitchHeading>
                      <TabsWrapper>
                        <VFCapsule activeBtn={activeCapsule} capsules={tabOptions} handleClick={handleTabChange} />
                      </TabsWrapper>
                    </TabSwitchContainer>
                    {getRMUI()}
                    <Note type="danger" message={message} />
                  </div>

                  <BlurCover style={{ display: hasProductGroup ? "none" : "block" }}>
                    <CardCover>
                      <DashedCard>
                        <MessageText>
                          Please select filter for product group to view estimated due
                          date
                        </MessageText>
                      </DashedCard>
                    </CardCover>
                  </BlurCover>
                </EstimatedWrapper>

              </BTRAllomentSection>
            </Allotment.Pane>
          </Allotment>



        </BTRTableWrapper>
        <FilterModal
          filters={filters}
          isOpen={isModalOpen}
          handleClose={handleModalToggle}
          handleOkay={() => applyFilter(selectedOptions)}
          selectedOptions={selectedOptions}
          handleOptionSelect={handleFilterSelect}
          handleNameChange={handleNameChange}
          themeUi={themeUi}
        />
      </div>
    </EnquiryWrapper>
  );
};

export default EnquiryResponse;
