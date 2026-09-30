import { useEffect, useState, useRef } from "react";
import FilterModal from "./FilterModal";
import ResizableTable from "./ResizableTable";
import MTOActionToolBar from "../../../../../../../src/components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import {
  BTRAllomentSection,
  EnquiryWrapper,
  FilterWrapper
} from "./styles";
import { useGetEnquiryResData } from "../../../../../Services/MTO/Production/EnquiryResponse";
import { useUserData } from "../../../../../../context/index";
import { notifyError, notifyLoader } from "../../../../../../helpers/notify";
import { toast } from "react-toastify"
import { useGetUIConfigData } from "../../../../../../VectorFlow/Services/MTO/Common/UIConfig";
import { getColumnDefinations } from "../../../../../../helpers/utils";
import FullkitCellRenderer from "../../../Common/FullKitCellRenderer/FullkitCellRenderer";
// import { valueContainerCSS } from "react-select/dist/declarations/src/components/containers";
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import OverlayLoader from "../../../Common/Loader";
import { ExcelExportName, UIGridCode } from "../../../Common/Enum";
import { format } from "date-fns";


const FOLSummary = () => {
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [tableData, setTableData] = useState<any>([]);
  const [filterData, setFilterData] = useState<any>([]);
  const [selectedFilters, setSelectedFilters] = useState<any>([]);
  const [currentGridRef, setCurrentGridRef] = useState<any>(null);
  const [columnState, setColumnState] = useState<any>([]);
  const [isReset, setIsReset] = useState<any>(undefined);
  const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
  const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
 
  const [selectedOptions, setSelectedOptions] = useState<any>({
    plantName: "",
    productGroup: [],
    department: {},
    ccrGroup: {},
    ccrName: {},
    folfilter: { symbol: '', value: '' }
  });
  const { user } = useUserData();
  // const {state:multiFilter,setState:setMultiFilter,onDelete} = useBPRFilter()
  const themeUi = user.user.theme_ui;
  const gridRef = useRef<any>(null);
  const [HeaderData, setHeaderData] = useState([]);
  const [myColDefs, setMyColDefs] = useState([{}]);
  const [masterUIConfig, setMasterUIConfig] = useState([]);

  const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
  const [userPageSize, setUserPageSize] = useState<any>();
  const [isPivot, setIsPivot] = useState<any>(false);


  // const { data } = useGetEnquiryResData() || {};
  const { data: FOLSummaryData } = useGetEnquiryResData() || {};



  const handleNameChange = (arr: any) => {
    setSelectedOptions((prev: any) => ({ ...prev, plantName: arr }));
  };

  const handleFolChange = (folfilterSymbol: string, folFilterValue: string) => {
    setSelectedOptions((prev: any) => ({ ...prev, folfilter: { symbol: folfilterSymbol, value: folFilterValue } }))
  }

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

  const filterByPlNames = (names: any) => {
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


  const filterByfol = (updata: any, folValues: any) => {
    const { symbol, value } = folValues;
    if (symbol.length === 0) {
      return updata;
    }
    if (value.length === 0) {
      return updata;
    }
    const updatedData = [];
    for (let i = 0; i < tableData?.length; i++) {
      const current = updata[i];

      if (symbol === '<') {

        if (Number(current?.fol) < Number(value)) {
          updatedData?.push(current);
        }
      }
      if (symbol === '>') {

        if (Number(current?.fol) > Number(value)) {
          updatedData?.push(current);
        }
      }
      if (symbol === '<=') {

        if (Number(current?.fol) <= Number(value)) {
          updatedData?.push(current);
        }
      }
      if (symbol === '>=') {

        if (Number(current?.fol) >= Number(value)) {
          updatedData?.push(current);
        }
      }
      if (symbol === 'Equal to') {

        if (Number(current?.fol) === Number(value)) {
          updatedData?.push(current);
        }
      }
      if (symbol === 'Not Equal to') {

        if (Number(current?.fol) !== Number(value)) {
          updatedData?.push(current);
        }
      }



    }
    return updatedData;
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
    if (options?.folfilter.value !== '') {
      filters.push({
        label: "FOL",
        values: [options.folfilter.symbol + " " + options.folfilter.value]
      })
    }

    setSelectedFilters(filters);
  }

  const applyFilter = (options: any) => {

    let data = [];
    data = filterByPlNames(options?.plantName);
    data = filterByfol(data, options?.folfilter);
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
    setFilterData(data);
    setIsModalOpen(false);
  };



  const productGroupOptions: any = [];
  const departmentOptions: any = [];
  const ccrGroupOptions: any = [];
  const ccrNameOptions: any = [];
  const plantOptions: any = [];
  const folOptions: any = [];

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
    {
      key: 'FOL',
      heading: 'fol Filter',
      options: folOptions
    }
  ];

  const removeFilters = (category: string, name: string) => {


    const updtedCCRName = selectedOptions?.ccrName;
    const updtedDept = selectedOptions?.department;
    const updtedCCRGrp = selectedOptions?.ccrGroup;
    let updatedPlantName = selectedOptions?.plantName;
    let updatedProductGrp = selectedOptions?.productGroup;
    let updatedFolFilter = selectedOptions?.folfilter;

    if (category === "FOL") {
      updatedFolFilter = { value: "", symbol: "" }
      setSelectedOptions((prev: any) => ({
        ...prev,
        folfilter: updatedFolFilter,
      }));
    }

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
      ccrName: updtedCCRName,
      folfilter: updatedFolFilter,
    });
    applyFilter({
      plantName: updatedPlantName,
      productGroup: updatedProductGrp,
      department: updtedDept,
      ccrGroup: updtedCCRGrp,
      ccrName: updtedCCRName,
      folfilter: updatedFolFilter
    });
  };


  
  const getEnquiryData = (data: any) => {
    try {
      setTableData(data?.data?.data);
    } catch (e) {
      console.log(e);
      notifyError('Failed to set Enquiry data!');
    }
  };
  
  useEffect(() => {
    notifyLoader("Loading Grid Data");
    if (FOLSummaryData?.data?.data && userConfigFetched) {
      getEnquiryData(FOLSummaryData);
    }
    toast.dismiss();
  }, [FOLSummaryData, userConfigFetched]);
  
  
  const savePageSize = (pageSize: any) => {
    if (pageSize) {
      setUserPageSize(pageSize);
      handleSaveClick(undefined, pageSize);
    } else {
      notifyError("Invalide page size");
    } 
  }

  const getUserColumnConfig = async () => {
    try {
      const data = await getUserUIReportConfigData({
        un: user.user.name,
        rn_id: UIGridCode.ProdFolSummary
      });

      const newConfig = data?.data?.data[0]?.columns_settings ? JSON.parse(data?.data?.data[0]?.columns_settings) : [];
      setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : undefined);
      setColumnState(newConfig.cs);
      setIsPivot(newConfig.pivot);
      setUserConfigFetched(true)

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
        const fullConfig = { pivot: false, cs: coldefs, pageSize: userPageSize };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdFolSummary,
          cs: JSON.stringify(fullConfig),
        };  
        await updateUserUIReportConfigData([payload]);
        setColumnState([...coldefs]);
        setIsPivot(false);
      } else if (page_size) {
        const fullConfig = { pivot: isPivot, cs: columnState, pageSize: page_size };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdFolSummary,
          cs: JSON.stringify(fullConfig),
        };  
        await updateUserUIReportConfigData([payload]);
  
      } else {
        if (currentGridRef?.current?.api) {
          const config = currentGridRef.current?.api.getColumnState();
          const isPivot = currentGridRef.current?.api.isPivotMode();
          const fullConfig = { pivot: isPivot, cs: config, pageSize: userPageSize };
          const payload = {
            un: user.user.name,
            rn_id: UIGridCode.ProdFolSummary,
            cs: JSON.stringify(fullConfig),
          };
  
          await updateUserUIReportConfigData([payload]);
          await getUserColumnConfig();
        }
      }
    } catch (error) {
      console.error(error);
    }
  };
  

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
    if (FOLSummaryData?.data?.data && userConfigFetched) {
      setTableData(FOLSummaryData?.data?.data);
    }
    toast.dismiss()
  }, [FOLSummaryData, userConfigFetched]);

  useEffect(() => {
    setFilterData(FOLSummaryData?.data?.data);
  }, [tableData]);

  const { mutateAsync: getUIConfigData } = useGetUIConfigData()

  const reportName = "EnquiryResponse";

  const setColumnDef = async () => {
    try {
      const response = await getUIConfigData(reportName);
      setHeaderData(response.data.data);
    }
    catch (e) {
      console.log(e);
    }
  }

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

  const onExcelExport = () => {
    // const exportName = `FOL_Summary_${format(Date.now(), "dd-MM-yyyy")}`;
    const exportName = ExcelExportName.FOL_Summary
    gridRef.current?.api?.exportDataAsExcel({
      fileName: exportName,
      sheetName: exportName 
    });
  }

  return (
    <EnquiryWrapper>
      {(isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />}
      <FilterWrapper>
        <MTOActionToolBar
          comp={"EnquiryResponse"}
          isAddFilterButton
          isAsOnDate
          isExcelExport
          onExcelExportClick={onExcelExport}
          onAddFilter={handleModalToggle}
          selectedFilters={selectedFilters}
          removeFilters={removeFilters}
          themeUi={themeUi}
          handleSaveClick={handleSaveClick}
          handleResetClick={handleResetClick}
        />
      </FilterWrapper>

      <BTRAllomentSection style={{ height: '70vh' }}>


        <ResizableTable 
          colDef={myColDefs} 
          gridRef = {gridRef}
          data={filterData}
          setCurrentGridRef={setCurrentGridRef}
          currentGridRef={currentGridRef}
          columnState={columnState}
          savePageSize={savePageSize}
          userPageSize={userPageSize}
          isPivot={isPivot}
        />
      </BTRAllomentSection>



      <FilterModal
        filters={filters}
        isOpen={isModalOpen}
        handleClose={handleModalToggle}
        handleOkay={() => applyFilter(selectedOptions)}
        selectedOptions={selectedOptions}
        handleOptionSelect={handleFilterSelect}
        handleNameChange={handleNameChange}
        themeUi={themeUi}
        handleFolChange={handleFolChange}
      />
    </EnquiryWrapper>
  );
};

export default FOLSummary;
