
import { ColumnHeaderConfig } from '../VectorFlow/types/ColumnHeaderConfig';
import { type NavigateFunction } from 'react-router'
import { LOCAL_STORAGE_KEY, ROUTES } from './constants'
import { notifyError} from './notify'
import { type Master, type Option, type Field, type Filter, MDMMasterState, DraftActionType,type NormHistory, type DailyData } from '../VectorFlow/types/MDM';
import readXlsxFile,{readSheetNames} from 'read-excel-file';
import { ColDef, ColGroupDef, CellClickedEvent } from 'ag-grid-community';
import { defaultColDefs, masterIdToDeleteSchemaMapper, masterIdToSchemaMapper, TaskPendingAvoidColumnsMapper, TaskPendingAvoidColumnsMapperSpecific, taskStatusCustomColDefs, mdmRoutes, seasonalityQuickFilterData, BTRDefaultColDefs, TaskPendingStopPIPOCustomColumns } from './MDMConstants';
import ActionRenderer from '../VectorFlow/Pages/MTA/MDM/SavedDrafts/ActionRenderer';
import { subDays, format, differenceInSeconds, parse } from 'date-fns';
//import { formatMDMDateFromat } from './format';
import { formatMDMDate } from './format';
import TaskPendingActionHeader from '../VectorFlow/Pages/MTA/MDM/TaskPendingForReview/TaskPendingActionHeader';
import TaskPendingActionRenderer from '../VectorFlow/Pages/MTA/MDM/TaskPendingForReview/TaskPendingActionRenderer';
import { UiConfigField } from '../VectorFlow/types/UIConfigFields';
import { BPRField, BPRViewTableFilterNumericalOperator, BPRViewTableFilterStringOperator } from '../VectorFlow/types/BPR';
import { RRRField } from '../VectorFlow/types/RRR'
import _ from 'lodash';
import { DBMField } from '../VectorFlow/types/DBM';
import { BPRViewTableHeaderFilterNumberoptions, BPRViewTableHeaderFilterStringoptions } from './BPRConstants';
import { BPRViewTableColDef } from '../VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR/BPRViewTable';
import { InputTypes } from '../VectorFlow/Pages/MTO/Common/Enum';
import { AgChartOptions } from "ag-charts-community";
// clear cached token and redirect to sso login
import CryptoJS from 'crypto-js';
import MTOActionRenderer from '../VectorFlow/Pages/MTO/MDM/SavedDrafts/MTOActionRenderer';
import { decryptStorageData } from '../VectorFlow/Pages/MTO/Common/encryption';
import { getNumberFormat } from './numberFormat';
import axios from 'axios';


const keyboardCharacters = [
  // '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
  'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
  'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
  'u', 'v', 'w', 'x', 'y', 'z',
  'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
  'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
  'U', 'V', 'W', 'X', 'Y', 'Z'
];

let isRedirecting = false;

export const setRedirecting = () => { isRedirecting = true; }
export const getRedirecting = () => isRedirecting;
export const clearRedirecting = () => { isRedirecting = false; }

export const completeLocalLogin = (navigate: NavigateFunction) => {
  clearRedirecting();
  navigate('/landing-page', { replace: true });
}

export const loginRedirect = (navigate?: NavigateFunction) => {

  if (getRedirecting()) return; // prevent multiple redirects
  setRedirecting();

  saveOriginalUrlBeforeLogin() 

   // Safer redirect (no back navigation to protected route)
   if (navigate) {
    navigate(ROUTES.landing, { replace: true });
  } else {
    window.location.replace(ROUTES.landing);
  }
}

export const login = (navigate: NavigateFunction) => {
  const localLogin = isTrue(process.env.REACT_APP_ENABLE_LOCAL_LOGIN)

  if (localLogin) {
    navigate(ROUTES.internalLogin, { replace: true })
  } else {
    window.location.href = String(process.env.REACT_APP_SSO_LOGIN_URL)
  }
}

export const hashPassword = (password: string): Promise<string> => {
  const iv = CryptoJS.lib.WordArray.random(16); 
  const encrypted = CryptoJS.AES.encrypt(password, CryptoJS.enc.Utf8.parse(process.env.REACT_APP_SECRET_KEY), {
    iv: iv,
    mode: CryptoJS.mode.CTR,
    padding: CryptoJS.pad.NoPadding,
  });
  const encryptedPassword = iv.concat(encrypted.ciphertext).toString(CryptoJS.enc.Base64);
  return encryptedPassword;
};

// save current url in session storage
const saveOriginalUrlBeforeLogin = () => {
  const pathname = window.location.pathname
  if (
    pathname !== '/' &&
    pathname !== ROUTES.logout &&
    pathname !== ROUTES.landing
  ) {
    sessionStorage.setItem(
      'original_url',
      window.location.pathname + window.location.search
    )
  }
}

// navigate to the original url after user login
export const getOriginalUrl = () => {
  const originalUrl = sessionStorage.getItem('original_url')
  const originalUrlType = sessionStorage.getItem('original_url_type')
  if (originalUrl || originalUrlType) {
    sessionStorage.removeItem('original_url')
    // original_url_type for external projects
    sessionStorage.removeItem('original_url_type')
  }
  return { url: originalUrl, type: originalUrlType }
}


/**
 * Utilities to compare between two variables with same supported types: string | number | boolean
 */
export const compare = <T = string | number | boolean>(a: T, b: T) => {
  if (a === b) return 0
  else if (a > b) return 1
  return -1
}

/**
 * Utilities to remove keys with value is undefined, null or empty
 * Useful for clearing parameter objects, to not display empty parameters in the url
 */
export const cleanObject = (object?: Record<string, any>) => {
  if (object == null) return {}
  Object.keys(object).forEach((key) => {
    const value = object[key]
    if (value === undefined || value === null || value === '') {
      delete object[key]
    }
  })
  return object
}

export const formatUpperCaseFirstLetter = (str: string) => {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

/*
 * Ignore operators that handled by imperva for sql injection
 */
export const sanitizeUserSearchText = (search: string) => {
  const value = search.trim()

  // 1. single quote: if only one and it's at the last place, Imperva consider it's sql injection
  if (
    value.split("'").length === 2 &&
    value.substring(value.length - 1) === "'"
  ) {
    return search.replace("'", '')
  }
  return search
}

export const isTrue = (value?: string | number) => {
  return (
    (typeof value === 'string' && value?.toUpperCase() === 'TRUE') ||
    value === 1
  )
}


export const mapVDRFieldsToColDefs = (fields: RRRField[]): ColDef[] => {

  let result: ColDef[] = [];
  result = fields?.map((f: RRRField) => {
    if (f.Col_Code === 'DispatchPen') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        hide: !f.Visible,
        cellRenderer: 'colorDispatchRender',
        cellDataType: getCellDataType(f.DataType),
        filter: getCellFilter(f.DataType)
      }
    }
    if (f.Col_Code === 'WHDescription') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        rowGroup: false,
        cellDataType: getCellDataType(f.DataType),
        filter: getCellFilter(f.DataType)
      }
    }
    return {
      colId: f.Col_Code,
      field: f.Col_Code,
      headerName: f.Header,
      hide: !f.Visible,
      cellDataType: getCellDataType(f.DataType),
      filter: getCellFilter(f.DataType)
    }

  })

  return result;

}

export const mapRRRColorBandWiseFieldsToColDefs = (fields:RRRField[],onOpenDailyDataGraph:any):ColDef[]=>{

  if(!fields || fields.length<1){
    return []
  }

  let result:ColDef[] = []

  const specificColumns:ColDef[] =[
    {
      colId:'dailydatagraph',
      field:'',
      headerName:'',
      width:40,
      lockPosition:'left',
      floatingFilter:false,
      tooltipField:"DailyDataGraph",
      cellRenderer:'grapCellRenderer',
      cellRendererParams:{
        onOpenDailyDataGraph:onOpenDailyDataGraph
      },
    }
  ]

  result =  fields.map((f:RRRField)=>{
    
    if(f.Col_Code==='DispatchColor'){
      return{
        colId:f.Col_Code,
        field:f.Col_Code,
        headerName:f.Header,
        hide:!f.Visible,
        cellRenderer:'colorCellRenderer',
        cellDataType:getCellDataType(f.DataType),
        filter:getCellFilter(f.DataType)
      }
    }
    return{
      colId:f.Col_Code,
      field:f.Col_Code,
      headerName:f.Header,
      hide:!f.Visible,
      cellDataType:getCellDataType(f.DataType),
      filter:getCellFilter(f.DataType)
    }
  })
  return [...result,...specificColumns]
}

export const mapOrderAllocationReportFieldsToColDefs = (fields:UiConfigField[],onOpenDailyDataGraph:any):ColDef[]=>{

  if(!fields || fields.length<1){
    return []
  }

  let result:ColDef[] = []

  const BORSpecificColumns:ColDef[] =[
    {
      colId:'dailydatagraph',
      field:'',
      headerName:'',
      width:40,
      lockPosition:'left',
      floatingFilter:false,
      tooltipField:"DailyDataGraph",
      cellRenderer:'grapCellRenderer',
      cellRendererParams:{
        onOpenDailyDataGraph:onOpenDailyDataGraph
      },
      
      

      // tooltipComponent:'remarksToolTipComponent'
    }
  ]



  result =  fields.map((f:UiConfigField)=>{


    if(f.Col_Code==='OrderColor'){
      return{
        colId:f.Col_Code,
        field:f.Col_Code,
        headerName:f.Header,
        hide:!f.Visible,
        floatingFilter:true,
        cellRenderer:'colorCellRenderer',
        filter:getCellFilter(f.DataType),
        cellDataType:getCellDataType(f.DataType)
      }
    }
    return{
      colId:f.Col_Code,
      field:f.Col_Code,
      headerName:f.Header,
      hide:!f.Visible,
      floatingFilter:true,
      filter:getCellFilter(f.DataType),
      cellDataType:getCellDataType(f.DataType)
    }
  })
  return [...result,...BORSpecificColumns]
}

export const mapBORColorBandWiseFieldsToColDefs = (fields:UiConfigField[],onOpenDailyDataGraph:any):ColDef[]=>{

  if(!fields || fields.length<1){
    return []
  }

  let result:ColDef[] = []

  const BORSpecificColumns:ColDef[] =[
    {
      colId:'dailydatagraph',
      field:'',
      headerName:'',
      width:40,
      lockPosition:'left',
      floatingFilter:false,
      tooltipField:"DailyDataGraph",
      cellRenderer:'grapCellRenderer',
      cellRendererParams:{
        onOpenDailyDataGraph:onOpenDailyDataGraph
      },
      
      

      // tooltipComponent:'remarksToolTipComponent'
    },
    {
      colId:'remarks',
      field:'remarks',
      headerName:'Remarks',
     cellRenderer:'submitRemarkCellRenderer',
     pinned:'right',
     editable:true,
     cellStyle:{
      overflow:'visible',
      'min-width':180,
    }
  }
  ]



  result =  fields.map((f:UiConfigField)=>{


    if(f.Col_Code==='DispatchColor'){
      return{
        colId:f.Col_Code,
        field:f.Col_Code,
        headerName:f.Header,
        hide:!f.Visible,
        floatingFilter:true,
        cellRenderer:'colorCellRenderer',
        filter:getCellFilter(f.DataType),
        cellDataType:getCellDataType(f.DataType)
      }
    }
    return{
      colId:f.Col_Code,
      field:f.Col_Code,
      headerName:f.Header,
      hide:!f.Visible,
      floatingFilter:true,
      filter:getCellFilter(f.DataType),
      cellDataType:getCellDataType(f.DataType)
    }
  })
  return [...result,...BORSpecificColumns]
}

export const mapTotalRequirementFieldsToColDefs = (fields:RRRField[]):ColDef[]=>{

  if(!fields || fields.length<1){
    return []
  }

  let result:ColDef[] = []

  result =  fields.map((f:RRRField)=>{
    
    if(f.Col_Code==='DispatchColor'){
      return{
        colId:f.Col_Code,
        field:f.Col_Code,
        headerName:f.Header,
        hide:!f.Visible,
        cellRenderer:'colorCellRenderer',
        cellDataType:getCellDataType(f.DataType),
        filter:getCellFilter(f.DataType)
      }
    }
    return{
      colId:f.Col_Code,
      field:f.Col_Code,
      headerName:f.Header,
      // hide:!f.Visible,
      cellDataType:getCellDataType(f.DataType),
      filter:getCellFilter(f.DataType)
    }
  })
  return [...result]
}


export const mapRRRFieldsToColDefs = (fields: RRRField[]): ColDef[] => {

  if (!fields || fields.length < 1) {
    return []
  }

  let result: ColDef[] = []

  // const RRRSpecificColumns: ColDef[] = [
  //   {
  //     colId: 'remarks',
  //     field: 'ramarks',
  //     headerName: 'Remarks',
  //     tooltipField: "tags"
  //   },
  //   {
  //     colId: 'rh',
  //     field: 'rh',
  //     headerName: 'Remark History',
  //   }
  // ]

  result = fields.map((f: RRRField) => {

    if (f.Col_Code === 'TPen') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        hide: !f.Visible,
        cellRenderer: 'colorTechCellRenderer',
        cellDataType: getCellDataType(f.DataType),
        filter: getCellFilter(f.DataType)
      }
    }
    if (f.Col_Code === 'EPen') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        hide: !f.Visible,
        cellRenderer: 'colorEcoCellRenderer',
        cellDataType: getCellDataType(f.DataType),
        filter: getCellFilter(f.DataType)
      }
    }

    if (f.Col_Code === 'DispatchPen') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        hide: !f.Visible,
        cellRenderer: 'colorDispatchRender',
        cellDataType: getCellDataType(f.DataType),
        filter: getCellFilter(f.DataType)
      }
    }
    return {
      colId: f.Col_Code,
      field: f.Col_Code,
      headerName: f.Header,
      hide: !f.Visible,
      cellDataType: getCellDataType(f.DataType),
      filter: getCellFilter(f.DataType)
    }
  })
  return [...result]
}

export const handleDownload = async (nameApi: string, nameFile: string) => {
  try {
    const response = await fetch(`${process.env.REACT_APP_API_HOST}${nameApi}`, {
      credentials: 'include',
    })
    // Convert response to blob object
    const blob = await response.blob()
    // Create download URL for blob object
    const url = URL.createObjectURL(blob)

    // Trigger download
    const link = document.createElement('a')
    link.href = url
    if (nameFile === '') {
      const temp = response.headers.get('content-disposition')?.split('=');
      if (temp) nameFile = temp[temp.length - 1];
      link.setAttribute('download', `${nameFile}`)
    }
    else {
      link.setAttribute('download', `${nameFile}.csv`)
    }
    document.body.appendChild(link)
    link.click()
    // Clean up download URL
    URL.revokeObjectURL(url);
    return true;
  } catch (error: any) {
    notifyError(error);
  }

}

export const handleDownloadMTOVF = async (reportName: string, downloadName: string) => {
  try{
        const encryptedUserId = localStorage.getItem('User-ID');
        const encryptedUserName = localStorage.getItem('User-Name');
        const decryptedUserId = await decryptStorageData(encryptedUserId);
        const decryptedUserName = await decryptStorageData(encryptedUserName);
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    if (decryptedUserId) headers['User-ID'] = decryptedUserId;
    if (decryptedUserName) headers['User-Name'] = decryptedUserName;
    
    const response = await fetch(`${process.env.REACT_APP_VF_API_HOST_MTO}/DownloadReportData/?report_name=${reportName}`, {
      headers,
      credentials: 'include',
    });
    if (!response.ok) {
      notifyError("Error while downloading")
    } else {
      // Convert response to blob object
      const blob = await response.blob()
      // Create download URL for blob object
      const url = URL.createObjectURL(blob)

      // Trigger download
      const link = document.createElement('a')
      link.href = url
      if (downloadName.length !== 0) {
        link.setAttribute('download', `${downloadName}`)
      } else {
        link.setAttribute('download', `ReportFile.zip`)
      }
      document.body.appendChild(link)
      link.click()
      // Clean up download URL
      URL.revokeObjectURL(url);
    }
  }
  catch(err){
    notifyError('Error while downloading');
  }
}


export const handleDownloadVF = async (reportName: string, downloadName:string) => {

  try {
    const response = await fetch(`${process.env.REACT_APP_API_HOST}api/mta/DownloadReports/${encodeURIComponent(reportName)}`, {
      credentials: 'include',
    })
    if (!response.ok) {
      notifyError("Error while downloading")
      return false;
    } else {
      // Convert response to blob object
      const blob = await response.blob()
      // Create download URL for blob object
      const url = URL.createObjectURL(blob)

      // Trigger download
      const link = document.createElement('a')
      link.href = url
      if (downloadName.length !== 0) {
        link.setAttribute('download', `${downloadName}`)
      } else {
        link.setAttribute('download', `ReportFile.zip`)
      }
      document.body.appendChild(link)
      link.click()
      // Clean up download URL
      URL.revokeObjectURL(url);
      return true;
    }
  } catch (error: any) {
    notifyError('Error while downloading');
    return false;
  }

}

export const handleDataProductFilter = (data: any) => {
  const filterDuplicateValues = (listData: any) => {
    const newListData = listData.filter((item: string, index: number) => {
      return listData.indexOf(item) == index
    })

    return newListData
  }

  let listCategory = [] as string[]
  let listStyle = [] as string[]
  let listFit = [] as string[]
  let listLaunchPeriod = [] as any[]
  let listSubBrand = [] as any[]
  let listBrand = [] as any[]

  listBrand = Object.keys(data).map((item: string) => ({
    value: item,
    label: item
  }))

  // list brand
  Object.keys(data).map((brand: any) => {
    listSubBrand = listSubBrand.concat(Object.keys(data[brand]).map((item: string) => ({
      value: item,
      label: item
    })))

    // list subBrand
    if (data[brand]) {
      Object.keys(data[brand]).map((subBrand: any) => {
        listCategory.push(...Object.keys(data[brand][subBrand]))

        // list category
        if (data[brand][subBrand]) {
          Object.keys(data[brand][subBrand]).map((category: any) => {
            listStyle.push(...Object.keys(data[brand][subBrand][category]))

            // List style
            if (data[brand][subBrand][category]) {
              Object.keys(data[brand][subBrand][category]).map((style: any) => {
                listFit.push(
                  ...Object.keys(data[brand][subBrand][category][style])
                )

                // list launch period
                if (data[brand][subBrand][category][style]) {
                  Object.keys(data[brand][subBrand][category][style]).map(
                    (fit: any) => {
                      listLaunchPeriod.push(
                        ...Object.values(
                          data[brand][subBrand][category][style][fit][0]
                        )
                      )
                    }
                  )
                }
              })
            }
          })
        }
      })
    }
  })

  listCategory = filterDuplicateValues(listCategory).map((item: string) => ({
    value: item,
    label: item
  }))
  listStyle = filterDuplicateValues(listStyle).map((item: string) => ({
    value: item,
    label: item
  }))
  listFit = filterDuplicateValues(listFit).map((item: string) => ({
    value: item,
    label: item
  }))
  listLaunchPeriod = filterDuplicateValues(listLaunchPeriod).map((item: string) => ({
    value: item,
    label: item
  }))

  return {
    listBrand,
    listSubBrand,
    listCategory,
    listStyle,
    listFit,
    listLaunchPeriod
  }
}

export const format_number = (num: number) => {
  function parseNumber(numb: any) {
    if (typeof numb === 'number') {
      // If the input is already a number, return it as is
      return numb
    } else if (typeof numb === 'string') {
      // If the input is a string, parse it and return an integer or a float
      if (numb.includes('.')) {
        return parseFloat(numb)
      } else {
        return parseInt(numb)
      }
    } else {
      // If the input is not a number or a string, return null
      return null
    }
  }

  if (num >= 9999999999) {
    // If the number is greater than or equal to 1 crore
    return {
      compare: '>',
      digits: 999,
      letter: 'Cr'
    }
  }

  const num_str = String(Math.floor(num)) // Convert the number to a string
  const num_len = num_str.length // Get the length of the string

  let digits: any = '0'
  let letter = ''
  // Calculate the number of digits and the letter representation
  if (num_str === '0') {
    letter = ''
  } else if ([1, 2, 3].includes(num_len)) {
    digits = num_str
    letter = 'R'
  } else if (num_len === 4) {
    digits = (num / 1000).toFixed(1)
    letter = 'K'
  } else if ([5, 6].includes(num_len)) {
    digits = Math.round(num / 1000).toString()
    letter = 'K'
  } else if (num_len === 7) {
    digits = (num / 100000).toFixed(1)
    letter = 'L'
  } else if (num_len === 8) {
    digits = Math.round(num / 100000).toString()
    letter = 'L'
  } else if (num_len === 9) {
    digits = (num / 10000000).toFixed(1)
    letter = 'Cr'
  } else if (num_len === 10) {
    digits = Math.round(num / 10000000).toString()
    letter = 'Cr'
  }
  digits = parseNumber(digits)
  // Combine the digits and letter representation into a single string
  return {
    compare: null,
    digits,
    letter
  }
}

// Helper Function to Dynamically Map Roles fetched from Backend to the Frontend as required by the ArrowList Component.
export const 
generateRolesObject = (roles:Array<object>) => {
  type Role = {
    id: number;
    title: string;
    status: boolean;
    child: Role[];
  };
  
  const rolesArray:Role [] = [];
  
  roles.forEach((role:any)=>{
    const roleObj = rolesArray.find((app:Role)=>app.id===role.application_id);
    if(roleObj){
      roleObj.child.push(role)
    }
    else{
      rolesArray.push({
        id:role.application_id,
        title:role.application_name,
        status:false,
        child:[role],
      })
    }
  })

  return rolesArray;
}

//Helper Roles to Generate Options as required for react-multiselect component
export const generateOptions = (data: Master[]) => {
  const temp: string[] = [];
  const options: Option[] = [];
  if (!data) return options
  data.forEach((master: Master) => {
    const tempMasterFields = [...master.fields]
    const tempFields = tempMasterFields.sort((a: Field, b: Field) => parseInt(a.col_Position) - parseInt(b.col_Position))
    tempFields.forEach((field: Field) => {
      if (!temp.includes(field.displayName) && field.visible) {
        temp.push(field.displayName);
        options.push({ value: field.key, label: field.displayName, })
      }
    })
  });
  return options;
}

export const generateRandomId = (length?: number) => {
  if (!length) {
    length = 10
  }

  let id = ''
  for (let index = 0; index < length; index++) {
    id = id + keyboardCharacters[Math.floor(Math.random() * keyboardCharacters.length)]

  }
  return id

}

export const replaceKeyWithDisplayName = (message: string, master: MDMMasterState) => {
  return new String(message).replaceAll(/"([^"]+)"/g, (m) => {
    const displayName = master.fields.find((f: Field) => f.key === m.replaceAll('"', ''))?.displayName;
    if (displayName) return displayName
    return m;
  })
}

export const checkError = (row: any, master: MDMMasterState, pageType: string) => {
  const masterSchema = pageType === 'remove' ? masterIdToDeleteSchemaMapper[master.id.toString()] : masterIdToSchemaMapper[master.id.toString()];
  let { error, warning }: any = masterSchema.validate(row, { context: row });
  if (error) error = replaceKeyWithDisplayName(error.message, master);
  if (warning) warning = replaceKeyWithDisplayName(warning.message, master);
  return { error, warning };
}

export const parseExcelData = async (file: any, master: MDMMasterState, pageType: string, selectedColumns: any,RECORD_UPLOAD_LIMIT?:any) => {

  const currMasterKeys = master.fields.map((field: Field) => field.key); //array containing keys of current master fields
  const result: object[] = [];
  const buffer = await file.arrayBuffer();

  let selectedKeys:any;

  //Selected Columns Keys
  if(pageType==='add'){
    selectedKeys = master.fields.filter((field:Field)=>field.isAdd).map((field:Field)=>field.key);
  }
  else{
    selectedKeys = selectedColumns.map((col:any)=>col.colId);
  }


  const numberOfSheets = await readSheetNames(file);
  if(numberOfSheets.length > 1){
    throw new Error('File cannot contain multiple sheets') 
  }

  if(numberOfSheets[0]!='ag-grid'){
    throw new Error('Sheet Name is changed') 
  }
   
  const data = await readXlsxFile(buffer,{
    parseNumber: (string:any) => string
  });
  
  //Check if File Contains a Column that is Duplicate
  const isDuplicateHeader = data[0].some((header:any,index:number)=>data[0].indexOf(header)!==index);

  if (data.length > parseInt(RECORD_UPLOAD_LIMIT || "50000")) {
    throw new Error(`Number of rows should not exceed ${RECORD_UPLOAD_LIMIT || '50000'}`);
  }
  
  if(isDuplicateHeader){
    throw new Error("File Contains Duplicate Headers")
  }

  //displayName to key mapper
  const headerKeys = data[0].map((headerName: any) => {
    const fieldObj = master.fields.find((field: Field) => field.displayName === headerName);
    if (fieldObj) return fieldObj.key;
    else return '';
  })



  if(master.id===501 || master.id===502 || master.id===503 || master.id===504){
    const objKeys: string[] = [];
    selectedColumns.forEach((ele:any)=>{
      objKeys.push(ele.colId);
    })

    const bufferData:any = [];
    for(let i=1; i< data.length; i++){
      const buffData:any = {};
      for(let j=0; j< data[i].length; j++){
        buffData[objKeys[j]]= data[i][j];
      }
      buffData["err"]= "";
      bufferData.push(buffData);
    }

    return bufferData;
  }

  let headers: any = [] //Not Selected Headers
  let error = false;


  if (pageType === 'modify') {

    //Check if File Contains a Column that is not Downloadabl;
    headerKeys.forEach((key: string) => {
      const fieldObj = master.fields.find((field: Field) => (field.key === key) && !field.isDownload)
      if (fieldObj) {
        headers.push(fieldObj.displayName);
        error = true;
      }
    })

    if (error) {
      throw new Error(`File Contains ${headers.join(', ')} field which are not allowed to Upload.`)
    }

  //Check if All Selected Keys are Present in The Uploaded
  selectedKeys.forEach((key: string) => {
    const fieldObj = master.fields.find((field: Field) => field.key === key)
    if (!headerKeys.includes(key) && fieldObj?.isDownload) {
      error = true;
      headers.push(master.fields.find((field: Field) => field.key === key)?.displayName)
    }
  })
}

  if (pageType == "add") {
    selectedKeys.forEach((key: string) => {
      const fieldObj = master.fields.find((field: Field) => field.key === key)
      if (!headerKeys.includes(key) && fieldObj?.isAdd) {
        error = true;
        headers.push(master.fields.find((field: Field) => field.key === key)?.displayName)
      }
    })
  }
  if (pageType == "remove") {
    selectedKeys.forEach((key: string) => {
      const fieldObj = master.fields.find((field: Field) => field.key === key)
      
      if (!headerKeys.includes(key) && fieldObj?.isDelete) {
        error = true;
        headers.push(master.fields.find((field: Field) => field.key === key)?.displayName)
      }

    })
  }

  if (error) {
    throw new Error(`File is missing the following columns: ${headers.join(', ')}`);
  }

  error = false;
  headers = [];

  headerKeys.forEach((key: string) => {

    if (!currMasterKeys.includes(key)) {
      throw new Error("Please Upload a Valid Master");
    }
    if (!selectedKeys.includes(key)) {
      error = true;
      headers.push(master.fields.find((field: Field) => field.key === key)?.displayName)
    }
  })

  if (error) {
    throw new Error(`File Contains ${headers.join(', ')} which were not selected`)
  }

  // let rowObj:any = {};
  // let temp = 0;
  if (data.slice(1).length === 0) {
    throw new Error(`File Contains zero rows.`)
  }
  // data.slice(1).map((row:any)=>{

  //   row.map((value:any)=>{
  //     const attributeName = headerKeys[temp];
  //     rowObj[attributeName.toString()] = "" + value;
  //     temp+=1;
  //   })
  //   temp = 0;
  //   //Replace with empty string if null (for Custom keys)
  //   Object.keys(rowObj).forEach((key:any)=>{
  //     if(customKeys.includes(key) && rowObj[key]===null){
  //       rowObj[key] = ''
  //     }
  //   })

  //   const {error,warning} = checkError(rowObj,master,pageType);

  //   if(error !== undefined){
  //     rowObj.error = error;
  //   }
  //   if(warning !== undefined){
  //     rowObj.warning = warning;
  //   }
  //   const doesRowExists = result.find((row:any)=>JSON.stringify(row)===JSON.stringify(rowObj));
  //   if(doesRowExists){
  //     throw new Error("Duplicate Rows Found in File");
  //   }
  //   result.push(rowObj);
  //   rowObj={}

  // })




  return result;
}

export const mapMasterToColumnDefs = (fields: Field[], masterId?: number, onShowChart?: any,pageType?:string) => {
  let result: any[] = []
  const tempFields = [...fields]
  tempFields.sort((a: Field, b: Field) => parseInt(a.col_Position) - parseInt(b.col_Position))
  result = tempFields.map((f: any) => {

    const cellFilter = getCellFilter(f.dataType)
    const cellDataType = getCellDataType(f.dataType)

    return {
      field: f.key,
      colId: f.key,
      headerName: f.displayName,
      hide: pageType==='add' ? !f.isAdd : !f.visible ,
      floatingFilter: true,
      filter: cellFilter,
      cellDataType: cellDataType,
      tooltipComponent: 'conflictErrorToolTip',
      suppressColumnsToolPanel: !f.isApplicable,
      valueFormatter: (params: any) => {
        if(params.value == null || params.value === undefined)  return ''
        else if (cellDataType === 'number') {
          const format = (process.env.REACT_APP_NUMBER_FORMAT || '').toUpperCase();
          const locale = format === 'USA' ? 'en-US' : format === 'IND' ? 'hi-IN' : undefined;
          if(locale) return params.value.toLocaleString(locale)
          else       return params.value.toString()
        }
        else return params.value.toString()
        // return (params.value === null || params.value === undefined) ? '' : params.value.toString();
      },
      valueGetter: (params: any) => {
        if (f.key === 'sts') {
          const id = params.data.sts
          return seasonalityQuickFilterData.find((s) => s.id.includes(id))?.label

        }

        // if (cellDataType === 'number') {
        //   return params.value === null || params.value === undefined
        //     ? ''
        //     : parseFloat(params.value).toLocaleString(); // Format number properly
        // }
        if(!params.data){
          return ''
        }
        return params.data[f.key]
      },
      // suppressColumnsToolPanel: f.isEdit ? false : true,
      ...defaultColDefs
    }
  })

  if (masterId == 10) {
    const seasonalityCheckboxColDef: ColDef = {
      field: 'checkbox',
      colId: 'checkbox',
      headerName: '',
      checkboxSelection: true,
      headerCheckboxSelection: true,
      headerCheckboxSelectionCurrentPageOnly: true,
      width: 50,
      resizable:false,
      suppressMenu: true,
    }
    const seasonalityColorColDef: ColDef = {
      field: 'color',
      colId: 'color',
      headerName: '',
      width: 3,
      minWidth: 3,
      cellRenderer: 'seasonalityColorCellRenderer',
      resizable:false,
      suppressMenu: true,
      
    }

    const seasonalityGraphColDef: ColDef = {
      field: 'graph',
      colId: 'graph',
      headerName: '',
      width: 40,
      cellRenderer: 'seasonalityGraphCellRenderer',
      cellRendererParams: {
        onShowChart: onShowChart
      },
        resizable:false,
      suppressMenu: true,
    }
    return [seasonalityColorColDef, seasonalityCheckboxColDef, seasonalityGraphColDef, ...result]
  }

  if (masterId == 6) {
    const PIPOCheckboxColDef: ColDef = {
      field: 'checkbox',
      colId: 'checkbox',
      headerName: '',
      checkboxSelection: true,
      headerCheckboxSelection: true,
      headerCheckboxSelectionCurrentPageOnly: true,
      resizable:false,
      suppressMenu: true,
      width: 50
    }
    return [PIPOCheckboxColDef, ...result]
  }
  return result;
}

export const areMasterFiltersValid = (masterFilters: Filter[]) => {
  for (let i = 0; i < masterFilters.length; i++) {
    if (masterFilters[i].field === "" || masterFilters[i].operator === "" || masterFilters[i].text === "") {
      return false
    }
  }
  return true
}

// export const getMasterFromMasterGroupMapper=(mapper:{})=>{
//   for (const masterGroupKey in mapper){
//     return 
//   }
// }


export const mapStateFiltersToPayload = (filters: Filter[]) => {
  return filters.map((filter: Filter) => ({ attributeName: filter.field, op: filter.operator, value: filter.text }))

}

export const mapMasterToMasterState = (masters: any[], onShowChart?: any,pageType?:string): MDMMasterState[] => {

  return  masters.map((master: Master) => ({
    id: master.id,
    name: master.name,
    fields: master.fields.sort((a:Field,b:Field)=>parseInt(a.col_Position) - parseInt(b.col_Position)),
    filters: [
      {
        id: generateRandomId(),
        masterId: master.id,
        field: '',
        operator: '',
        text: ''
      }],
    colDefs: mapMasterToColumnDefs(master.fields, master.id, onShowChart,pageType),
    rowData: [],
    progress: 'default',
    isChecked: true,
    isMTO: true
  }))
}

export const mapDraftToColumnDefs = (fields: Field[], customParams?: ColDef) => {
  let result: ColDef[] = []
  result = fields.map((f) => {
    return {
      field: f.key,
      colId: f.key,
      headerName: f.displayName,
      minWidth: 180,

      cellStyle: {
        "textAlign": "center",
      },
      flex: 1,
      cellRenderer: f.key === "action" && ActionRenderer,
      ...customParams
    }
  })
  return result
}

export const mapTaskStatusToColDefs = (taskStatus: ColDef[], color: string) => {
  let result: ColDef[] = []
  result = taskStatus.map((t: ColDef) => {
    return {
      ...t,
      minWidth: 180,
      cellStyle: {
        "textAlign": "center",
        'overflow': 'hidden',
        'textOverflow': 'ellipsis',
        'whiteSpace': 'nowrap',
        // 'padding-top': '7px',
        'fontWeight': t?.colId === 'TaskStatus' ? '500' : 'auto',
        'color': t?.colId === 'TaskStatus' ? color : 'black',
        'cursor': t?.colId === 'TaskStatus' ? 'pointer' : 'default'
      },
      onCellClicked: (params: CellClickedEvent) => {
        if (params.colDef.colId === 'TaskStatus') {
          params.node.setExpanded(!params.node.expanded)
        }
      },
      flex: 1,
      floatingFilter: true,
      filter: "agMultiColumnFilter"
    }
  })
  return result
}

export const mapPendingTaskToColumnDefs = (colDefs: ColDef[]): ColDef[] => {
  return colDefs.map((colDef: ColDef) => {
    return {
      ...colDef,
      floatingFilter: true,
      filter: "agMultiColumnFilter",
      minWidth: 180,
      cellStyle: (params) => {
        if (params.colDef.colId === 'TaskName') return { "text-align": "center", 'color': 'rgb(188, 61, 129)', 'text-decoration': 'none', 'text-underline-offset': '7px', 'cursor': 'pointer', 'font-weight': '500' }
        return {
          "text-align": "center",
          'color': 'back',
          'text-decoration': 'none',
          'text-underline-offset': '0px',
          'cursor': 'auto',
          'font-weight': '400'
        }
      },
      flex: 1,
    }
  })
}

export const mapRowDataWithSrNo = (rowData: any[]) => {
  let result = []
  if (!rowData) return []
  result = rowData

  // result  = rowData.map((row)=>{
  //   return{
  //     ...row,
  //     PendingSince:formatMDMDate(row.PendingSince)
  //   }
  // })

  result.sort((a, b): any => {
    const date1 = parse(b.PendingSince, "dd/MM/yyyy hh:mm a", new Date());
    const date2 = parse(a.PendingSince, "dd/MM/yyyy hh:mm a", new Date());
    // console.log(differenceInSeconds("31/01/2024 05:29 PM","05/02/2024 11:38 AM"))
    return differenceInSeconds(date1, date2)
  })

  result = result.map((row: any, index: number) => {
    return {
      ...row,
      SrNo: index + 1
    }
  })
  return result
}


export const mapDraftDataToTableRowData = (rowData: any[]) => {
  let result = []
  if (!rowData) return
  result = rowData.map((row) => {
    return {
      ...row,
      LastModifiedDateTime: formatMDMDate(row.LastModifiedDateTime)
    }
  })

  result.sort((a, b): any => {
    return differenceInSeconds(b.LastModifiedDateTime, a.LastModifiedDateTime)
  })

  result = result.map((r: any, index: number) => {
    return { ...r, sr_no: index + 1, LastModifiedDateTime: format(r.LastModifiedDateTime, 'dd/MM/yy hh:mm:ss a') }
  })
  return result
}

export const getExistingColumns = (rowData: any) => {
  return Object.keys(rowData)
}

export const getExistingColumnFields = (columns: string[], fields: Field[]): Field[] => {
  const updatedFields: Field[] = []
  columns.map((c: string) => {
    fields.find((f: Field) => {
      if (f.key === c) updatedFields.push(f)
    })
  })
  return updatedFields
}

// export const areValuesEqual = (a: any, b: any): boolean => {
//   if (!Number.isNaN(parseInt(a)) && !Number.isNaN(parseInt(b))) {
//     // return parseFloat(a).toFixed(0) === parseFloat(b).toFixed(0)
//     return parseFloat(a) === parseFloat(b) 
//   }  
//   return a === b
// }
export const areValuesEqual = (a: any, b: any): boolean => {

  const numA = Number(a);
  const numB = Number(b);

  const isAValidNumber = a !== '' && a !== null && !Number.isNaN(numA) && Number.isFinite(numA);
  const isBValidNumber = b !== '' && b !== null && !Number.isNaN(numB) && Number.isFinite(numB);

  if (isAValidNumber && isBValidNumber) {
    return numA === numB;
  }

  return a === b;
};
export const mapMasterToColumnGroupDefs = (existingColumnsFields: Field[], masterId: number, themeUi: string, tasktype?: string, showApproveAllModal?: any, showRejectAllModal?: any, actionStatus?: string , isDisabled?:boolean): ColGroupDef[] | ColDef[] | Array<any> => {

  const textColor = themeUi === "REGALBLAZE" ? "#FCA311" : "#BC3D81"

  const sortedFields = existingColumnsFields.sort((a: Field, b: Field) => {
    return parseInt(a.col_Position) - parseInt(b.col_Position)
  })

  const colDefs = sortedFields.flatMap((f: Field) => {
    const isReferenceColumn = TaskPendingAvoidColumnsMapperSpecific[masterId]?.includes(f.key)


    if (masterId === 10) {
      if (f.key === 'sts') {
        return {
          headerName: "Requested For",
          field: f.key,
          colId: f.key,
          hide: !f.visible,
          suppressSpanHeaderHeight: true,
          valueFormatter: () => 'Stop',
          ...defaultColDefs,
          cellStyle: () => {
            return {
              "color": textColor,
              "text-align": "center",
              "border-left": "solid 1px #B9B9B9",
            }
          }
        }
      }
      return {
        headerName: f.displayName,
        field: f.key,
        colId: f.key,
        hide: !f.visible,
        suppressSpanHeaderHeight: true,
        pinned: TaskPendingAvoidColumnsMapper[masterId].includes(f.key) ? 'left' : false,
        ...defaultColDefs,
        cellStyle: () => {
          return {
            "color": !TaskPendingAvoidColumnsMapper[masterId].includes(f.key) ? textColor : 'black',
            "text-align": "center",
            "border-left": "solid 1px #B9B9B9",
          }
        }
      }

    }
    const descriptioncoldefs = {
      headerName: f.displayName,
      field: f.key,
      colId: f.key,
      hide: !f.visible,
      suppressSpanHeaderHeight: true,
      ...defaultColDefs
    }
    if (
      isReferenceColumn &&
      !((tasktype === "add" || tasktype === "modify") && (masterId === 1 || masterId === 2))
    ) {
      return descriptioncoldefs;
    }
    
    if (TaskPendingAvoidColumnsMapper[masterId].includes(f.key)) {
      return {
        headerName: f.displayName,
        field: f.key,
        colId: f.key,
        hide: !f.visible,
        suppressSpanHeaderHeight: true,
        pinned: 'left',
        ...defaultColDefs
      }
    }

    if (tasktype === "add" || masterId === 6) {
      if (masterId === 13) {
        return {
          headerName: f.displayName,
          field: f.key,
          colId: f.key,
          hide: !f.visible,
          children: [
            {
              headerName: 'New ' + f.displayName,
              field: 'New' + f.key,
              colId: 'New' + f.key,
              cellStyle: (params: any) => {
                return {
                  "color": !areValuesEqual(params.data[`New${f.key}`], params.data[`Old${f.key}`]) ? textColor : 'black',
                  "text-align": "center",
                  "border-left": "solid 1px #B9B9B9",
                }
              }
            },
            {
              headerName: 'Old ' + f.displayName,
              field: 'Old' + f.key,
              colId: 'Old' + f.key,
              cellStyle: {
                "text-align": "center",
                "border-right": "solid 1px #B9B9B9"
              }
            }
          ],
          ...defaultColDefs,

        }
      }
      return {
        headerName: f.displayName,
        field: f.key,
        colId: f.key,
        hide: !f.visible,
        children: [
          {
            headerName: 'Add ' + f.displayName,
            field: 'Add' + f.key,
            colId: 'Add' + f.key,
            cellStyle: {
              "color": textColor,
              "text-align": "center",
              "border-left": "solid 1px #B9B9B9",
            }
          }
        ],
        ...defaultColDefs,

      }
    }

    if (tasktype === "remove") {
      return {
        headerName: f.displayName,
        field: f.key,
        colId: f.key,
        hide: !f.visible,
        children: [
          {
            headerName: 'Delete ' + f.displayName,
            field: 'Delete' + f.key,
            colId: 'Delete' + f.key,
            cellStyle: {
              "color": textColor,
              "text-align": "center",
              "border-left": "solid 1px #B9B9B9",
            }
          }
        ],
        ...defaultColDefs,

      }
    }

    const modifycoldefs = {
      headerName: f.displayName,
      field: f.key,
      colId: f.key,
      hide: !f.visible,
      children: [
        {
          headerName: 'New ' + f.displayName,
          field: 'New' + f.key,
          colId: 'New' + f.key,
          valueFormatter: (params: any) => {
            if (areValuesEqual(params.data[`New${f.key}`], params.data[`Old${f.key}`])) {
              return '';
            }
            return params.value;
          },
          cellStyle: (params: any) => {
            return {
              "color": !areValuesEqual(params.data[`New${f.key}`], params.data[`Old${f.key}`]) ? textColor : 'black',
              "font-weight": !areValuesEqual(params.data[`New${f.key}`], params.data[`Old${f.key}`]) ? '700' : '300',
              "text-align": "center",
              "border-left": "solid 1px #B9B9B9",
            }
          }
        },
        {
          headerName: 'Old ' + f.displayName,
          field: 'Old' + f.key,
          colId: 'Old' + f.key,
          valueFormatter: (params: any) => {
            if (areValuesEqual(params.data[`New${f.key}`], params.data[`Old${f.key}`])) {
              return '';
            }
            return params.value;
          },
          cellStyle: {
            "text-align": "center",
            "border-right": "solid 1px #B9B9B9"
          }
        }
      ],
      ...defaultColDefs,

    }
    if(masterId==1 || masterId==2)
      return [descriptioncoldefs, modifycoldefs];
    else {
      return modifycoldefs;
    }
  })

  const taskPendingCustomColDefs: any[] = [
    {
      field: 'action',
      colId: 'action',
      headerName: 'Action',
      children: [
        {
          headerComponent: TaskPendingActionHeader,
          headerComponentParams: {
            disabled:isDisabled,
            showApproveAllModal: showApproveAllModal,
            showRejectAllModal: showRejectAllModal,
            actionStatus: actionStatus
          },
          cellRenderer: TaskPendingActionRenderer,
          width: 290,
          resizable:false,
          cellStyle: {
            "border-left": "solid 1px #B9B9B9",
          },
          pinned: 'right',
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
      field: 'status',
      colId: 'status',
      headerName: 'Status',
      suppressSpanHeaderHeight: true,
      cellStyle: {
        "border-right": "solid 1px #B9B9B9",
        "border-left": "solid 1px #B9B9B9",
        "text-align": 'center'
      },
      flex: 1,
      minWidth: 100
    },
    {
      field: 'comments',
      colId: 'comments',
      headerName: 'Comments',
      suppressSpanHeaderHeight: true,
      editable: (params: any) => {
        if (tasktype !== 'modify') return true
        if (tasktype === 'modify' && params.data.isModified) {
          return true
        }
        return false
      },
      ...defaultColDefs
    }
  ]

  if (masterId === 6) {
    return [
      TaskPendingStopPIPOCustomColumns[0],
      ...colDefs,
      {
        colId: "norm",
        headerName: "Norm",
        field: 'norm',
        children: [
          {
            colId: "targetNorm",
            headerName: "Target Norm",
            field: 'targetNorm',
            cellStyle: {
              color: textColor,
              "border-left": "solid 1px #B9B9B9",
              'text-align': 'center',
              fontWeight: 500
            }
          },
          {
            colId: "originalNorm",
            headerName: "Original Norm",
            field: 'originalNorm',
            cellStyle: {
              "border-right": "solid 1px #B9B9B9",
              'text-align': 'center',
              fontWeight: 500
            }
          }
        ]
      },
      TaskPendingStopPIPOCustomColumns[2],
      ...taskPendingCustomColDefs
    ]
  }

  if (masterId === 10) {
    return [
      ...colDefs,
      taskPendingCustomColDefs[0],
      taskPendingCustomColDefs[1],
      {
        field: 'comments',
        colId: 'comments',
        headerName: 'Comments',
        suppressSpanHeaderHeight: true,
        onCellClicked: (params: any) => console.log(params.data),
        editable: true,
        ...defaultColDefs
      }
    ].filter((c) => c.colId !== 'cmt')
  }

  return [
    //   {
    //   field:'checkbox',
    //   colId:'checkbox',
    //   headerName:'',
    //   checkboxSelection:true,
    //   headerCheckboxSelection:true,
    //   headerCheckboxSelectionCurrentPageOnly:true,
    //   width:10
    // }
    ...taskPendingCustomColDefs ,...colDefs]
}

export const mapMasterToTaskStatusColumnGroupDefs = (currentTaskMasterId: number, existingColumnsFields: Field[], masterId: number, tasktype?: string): ColGroupDef[] | ColDef[] => {

  const colDefs = existingColumnsFields.map((f: Field) => {


    if (tasktype === "add") {
      return {
        headerName: f.displayName,
        field: f.key,
        colId: f.key,
        hide: !f.visible,
        ...defaultColDefs,

      }
    }

    if (tasktype === "remove") {
      return {
        headerName: f.displayName,
        field: f.key,
        colId: f.key,
        hide: !f.visible,
        ...defaultColDefs,

      }
    }

    if (tasktype === "modify" && (currentTaskMasterId == 6 || currentTaskMasterId == 10)) {
      return {
        headerName: f.displayName,
        field: f.key,
        colId: f.key,
        hide: !f.visible,
        ...defaultColDefs,

      }
    }

    return {
      headerName: f.displayName,
      field: f.key,
      colId: f.key,
      hide: !f.visible,
      children: [
        {
          headerName: 'New ' + f.displayName,
          field: 'New' + f.key,
          colId: 'New' + f.key,
          cellStyle: {
            "color": '#BC3D81',
            "text-align": "center",
            "border-left": "solid 1px #B9B9B9",
          }
        },
        {
          headerName: 'Old ' + f.displayName,
          field: 'Old' + f.key,
          colId: 'Old' + f.key,
          cellStyle: {
            "text-align": "center",
            "border-right": "solid 1px #B9B9B9"
          }
        }
      ],
      ...defaultColDefs,

    }
  })

  return [...colDefs, ...taskStatusCustomColDefs]
}


  export const mapNewAndOldMasterRowDataToCustomRowData = (dirtyRowData: any[], existingColumnFields: Field[], taskType: string, masterId: number) => {
    const response = dirtyRowData?.map(entry => {
      

      if (((taskType === 'modify' && masterId !== 6 && masterId !== 10) || masterId === 13)) {
        const oldData = JSON.parse(entry.old);
        const newData = JSON.parse(entry.new);


        const oldDataPrefixed: any = {};
        const newDataPrefixed: any = {};
        let isRowModified = false // A flag to check equality of the current and previous rows
        existingColumnFields.map((f: Field) => {
          const isReferenceException = taskType === "add" && (masterId === 1 || masterId === 2)

          const isAvoidColumn =
            !isReferenceException &&
            (
              TaskPendingAvoidColumnsMapper[masterId].includes(f.key) ||
              TaskPendingAvoidColumnsMapperSpecific[masterId]?.includes(f.key)
            )

          if (!areValuesEqual(oldData[f.key], newData[f.key])) {

            isRowModified = true
          }
          const isSdModifyReference =
            taskType === "modify" &&
            (masterId === 1 || masterId === 2) &&
            (f.key === "sd" || f.key === "wd")

          if (isAvoidColumn && !isSdModifyReference) {
            newDataPrefixed[f.key] = String(newData[f.key] !== undefined ? newData[f.key] : "")
          }

          else {
            oldDataPrefixed[`Old${f.key}`] = String(oldData[f.key] !== undefined ? oldData[f.key] : "")
            newDataPrefixed[`New${f.key}`] = String(newData[f.key] !== undefined ? newData[f.key] : "")

            if (isSdModifyReference) {
              newDataPrefixed[f.key] = String(oldData[f.key] !== undefined ? oldData[f.key] : "")
            }
          } 
        })
        return {
          ...oldDataPrefixed,
          ...newDataPrefixed,
          status:!isRowModified?"Rejected" :"",
          comments: isRowModified ? '' : 'No modifications made in this record',
          isModified: isRowModified
        };
      }
      const dataPrefixed1: any = {};
      if( (masterId === 6 || masterId === 10) && taskType === 'modify'){
        existingColumnFields.map((f: Field) => {
        dataPrefixed1[f.key] = String(entry[f.key] !== undefined ? entry[f.key] : '')
        })
        return {
          ...dataPrefixed1,
          isModified:true,
          comments:  '',
          status: ''
        };
      }
      const data = entry;


      const dataPrefixed: any = {};



      existingColumnFields.map((f: Field) => {
        const isReferenceException = taskType === "add" && (f.key=="sd" || f.key=="wd") && (masterId === 1 || masterId === 2)

        const isAvoidColumn =
          !isReferenceException &&
          (
            TaskPendingAvoidColumnsMapper[masterId].includes(f.key) ||
            TaskPendingAvoidColumnsMapperSpecific[masterId]?.includes(f.key)
          )

        if (taskType === 'add') {
          if (!isAvoidColumn) {
            dataPrefixed[`Add${f.key}`] = String(data[f.key] !== undefined ? data[f.key] : '')
          }
          else {
            dataPrefixed[f.key] = String(data[f.key] !== undefined ? data[f.key] : '')
          }
        }
        else {

          if (masterId === 10) {
            dataPrefixed[f.key] = data[f.key]
          }
          //delete
          else {
            if (!isAvoidColumn) {
              dataPrefixed[`Delete${f.key}`] = String(data[f.key] !== undefined ? data[f.key] : '')
            }
            else {
              dataPrefixed[f.key] = String(data[f.key] !== undefined ? data[f.key] : '')
            }
          }
        }
      })
      return {
        ...dataPrefixed,
        isModified: true,
        status: '',
        comments: data.cmt ? data.cmt : ''
      };

    });

    // sort the rows wrt the isModified flag
    response?.sort((a: any, b: any) => {
      return b.isModified - a.isModified
    })
    return response
  }

export const mapTaskStatusDataToRowData = (currentTaskMasterId: number, dirtyRowData: any[], existingColumnFields: Field[], taskType: string) => {

  return dirtyRowData.map(entry => {

    if (taskType === 'modify' && currentTaskMasterId != 6 && currentTaskMasterId!=10  ) {

      const oldData = JSON.parse(entry.old);
      const newData = JSON.parse(entry.new);


      const oldDataPrefixed: any = {};
      const newDataPrefixed: any = {};


      existingColumnFields.map((f: Field) => {


        oldDataPrefixed[`Old${f.key}`] = oldData[f.key]
        newDataPrefixed[`New${f.key}`] = newData[f.key]
        newDataPrefixed['status'] = oldData['Status']
        newDataPrefixed['comments'] = oldData['Comments']

      })
      return {
        ...oldDataPrefixed,
        ...newDataPrefixed
      };
    }
    const data = entry;


    const dataPrefixed: any = {};



    existingColumnFields.map((f: Field) => {
      dataPrefixed['status'] = data['Status']
      dataPrefixed['comments'] = data['Comments']

      if (taskType === 'add') {

        dataPrefixed[f.key] = data[f.key]


      }
      else {

        dataPrefixed[f.key] = data[f.key]

      }
    })
    return {
      ...dataPrefixed
    };

  });
}


export const getActionName = (id: number): DraftActionType => {
  if (id === 1) return { id: 1, label: 'add', value: 'add' }
  if (id === 2) return { id: 2, label: 'view-modify', value: 'modify' }
  if (id === 3) return { id: 3, label: 'delete', value: 'remove' }
  throw new Error('Invalid action id')
}

export const getActionId = (actionName: string): DraftActionType => {
  if (actionName === "add") return { id: 1, label: 'add', value: 'add' }
  if (actionName === "view-modify" || actionName === "modify") return { id: 2, label: 'view-modify', value: 'modify' }
  if (actionName === "delete") return { id: 3, label: 'delete', value: 'remove' }
  throw new Error('Invalid action Name')
}

export const formatAndValidateDraftRowData = (colDefs:Array<ColDef>,rowData:Array<any>):Array<any>=>{
  const result = [...rowData]
  
  result.forEach((row)=>{
    colDefs.forEach((col)=>{
      if(col.colId && row[col.colId]){
        // if(col.cellDataType === "number"){
        //   row[col.colId] = parseFloat(row[col.colId])
        // }
      }
    })
  })

  return result
}


export const createMastersStateFromDraftData = (draftData: any[], fields: Master[]): MDMMasterState[] => {

  const masters: MDMMasterState[] = []
  draftData.map((master) => {
    const existingMaster = fields.find((m: Master) => m.id == master.MasterId)
    if (existingMaster) {
      const colDefs = master.GridState.length > 0 ? JSON.parse(master.GridState) : mapMasterToColumnDefs(existingMaster.fields, existingMaster.id)
      const updatedColDefs = colDefs.map((colDef: any) => {
        if (colDef.cellDataType) {
          colDef.cellDataType = 'text';
        }
        return colDef;
      });

      masters.push({
        id: existingMaster.id,
        name: existingMaster.name,
        colDefs: updatedColDefs,
        rowData: master.DataMaster? formatAndValidateDraftRowData(colDefs,master?.DataMaster)  : [],
        isChecked: true,
        filters: [{
          id: generateRandomId(),
          masterId: existingMaster.id,
          field: '',
          operator: '',
          text: ''
        }],
        progress: master.Status,
        fields: existingMaster.fields
      })
    }
  })

  return masters
}
export const getUploadModalRadioButtons = (masterId: number) => {
  if (masterId == 11 || masterId == 12) {
    return [
      {
        label: 'Absolute Value',
        value: 11
      },
      {
        label: 'Delta Percentage',
        value: 12
      }
    ]
  }
  if (masterId == 7 || masterId == 8 || masterId == 9) {
    return [
      {
        label: 'Phase Out',
        value: 7
      },
      {
        label: 'Phase In Phase Out',
        value: 8
      },
      {
        label: 'Target Norm',
        value: 9
      }
    ]
  }
  return []
}
export const getDatesBetween = (startDate: Date, endDate: Date) => {
  const currentDate = new Date(startDate.getTime());
  const dates = [];
  while (currentDate <= endDate) {
    dates.push(new Date(currentDate));
    currentDate.setDate(currentDate.getDate() + 1);
  }
  return dates;
}

export const getFormattedDate = (date: Date) => {
  const splitDateArray = date.toDateString().split(' ');
  return `${splitDateArray[2]} ${splitDateArray[1]} ${date.getFullYear()}`
}

export const generateSesonalityChartData = (row: any, data: any) => {
  let maxNorm = 0;
  let maxStockAndGit = 0;
  data.norm.forEach((o: NormHistory) => {
    const localMaxima = Math.max(+o.old_norm, +o.new_norm)
    if (maxNorm < localMaxima) {
      maxNorm = localMaxima;
    }
  })
  data.dailyData.forEach((o: DailyData) => {
    const stockAndGit = parseInt(o.stock, 10) + parseInt(o.git, 10)
    if (maxStockAndGit < stockAndGit) {
      maxStockAndGit = stockAndGit;
    }
  })
  const maxQuantity = Math.max(maxNorm, maxStockAndGit);
  // const xAxisLabels = data.dailyData.map((o:DailyData)=>getFormattedDate(new Date(o.date)));
  const todaysDate = new Date();

  const xAxisLabels = getDatesBetween(subDays(new Date(row.sd), Math.max(row.bd, row.r)), new Date(row.ed));

  // const xAxisLabels = genedata.dailyData.map((o:DailyData)=>new Date(o.date));
  const xAxisLablesFormatted = xAxisLabels.map((date: Date) => getFormattedDate(date));

  const seasonalityDates = getDatesBetween(new Date(row.sd), new Date(row.ed));

  // console.log("Seasonality Dates",seasonalityDates)

  const buildUpDuration = getDatesBetween(subDays(new Date(row.sd), row.bd), new Date(row.sd));

  const buildUpDurationData = xAxisLabels.map((date: Date) => {
    if (buildUpDuration.find((sd: Date) => +sd === +date)) return maxQuantity;
    return undefined;
  })

  const rlt = getDatesBetween(subDays(new Date(row.sd), row.r), new Date(row.sd));

  const rltData = xAxisLabels.map((date: Date) => {
    if (rlt.find((sd: Date) => +sd === +date)) return maxQuantity;
    return undefined;
  })


  const seasonData = xAxisLabels.map((date: Date) => {
    if (seasonalityDates.find((sd: Date) => +sd === +date)) return maxQuantity;
    return undefined
  })


  // const stockData = data.dailyData.map((o:DailyData)=>{
  //   const doesDateExist = xAxisLabels.find((date:Date)=> {    
  //     return +date === +new Date(o.date)
  //   })
  //   if(doesDateExist) return parseInt(o.stock,10)
  //   return 0;
  //   // return parseInt(o.stock,10)
  // });

  const stockData = xAxisLabels.map((date: Date) => {
    const isDailyDataPresent = data.dailyData.find((d: DailyData) => +new Date(d.date) === +date);
    if (isDailyDataPresent) {
      return isDailyDataPresent.stock
    }
    return 0;
  })

  const gitData = xAxisLabels.map((date: Date) => {
    const isDailyDataPresent = data.dailyData.find((d: DailyData) => +new Date(d.date) === +date);
    if (isDailyDataPresent) {
      return isDailyDataPresent.git
    }
    return 0;
  })

  const pointRadius: any[] = [];
  let tempNorm = 0; //used for filling data when norm not changed in below function
  // const normData = data.dailyData.map((d:DailyData)=>{
  //   const closestNormChange:NormHistory = data.norm.find((o:NormHistory)=>+(new Date(o.date)) === +(new Date(d.date)));
  //   if(closestNormChange) {
  //     tempNorm = parseInt(closestNormChange.new_norm,10);
  //     pointRadius.push(5);
  //     return parseInt(closestNormChange.new_norm,10)
  //   }
  //   pointRadius.push(0)
  //   return tempNorm;
  // })


  const normData = xAxisLabels.map((date: Date) => {
    const closestNormChange: NormHistory = data.norm.find((o: NormHistory) => +(new Date(o.date)) === +(new Date(date)));
    if (+date > +todaysDate) return undefined;
    if (closestNormChange) {
      tempNorm = parseInt(closestNormChange.new_norm, 10);
      pointRadius.push(5);
      return parseInt(closestNormChange.new_norm, 10)
    }
    pointRadius.push(0)
    return tempNorm;
  })

  const chartData = {
    labels: xAxisLablesFormatted,
    datasets: [
      {
        type: 'line' as const,
        label: 'Norm',
        borderColor: '#002060',
        borderWidth: 3,
        data: normData,
        pointBackgroundColor: "#00B0F0",
        pointStyle: 'circle',
        pointRadius: pointRadius,
      },
      {
        type: 'line' as const,
        label: 'Season',
        borderWidth: 0,
        fill: {
          target: 'origin',
          above: 'rgba(207, 167, 187, 0.4)'
        },
        data: seasonData,
        pointBackgroundColor: "rgba(207, 167, 187, 0.4)",
        pointStyle: 'rect',
      },
      {
        type: 'line' as const,
        label: 'BuildUpDuration',
        borderWidth: 0,
        fill: {
          target: 'origin',
          above: 'rgba(127, 0, 255, 0.4)'
        },
        data: buildUpDurationData,
        pointRadius: 0,
        pointStyle: 'rect',
        pointBackgroundColor: "rgba(127, 0, 255, 0.4)",
      },
      {
        type: 'line' as const,
        label: 'RLT',
        borderWidth: 0,
        fill: {
          target: 'origin',
          above: 'rgba(9, 38, 53, 0.4)'
        },
        data: rltData,
        pointRadius: 0,
        pointStyle: 'rect',
        pointBackgroundColor: "rgba(9, 38, 53, 0.4)",
      },
      {
        type: 'bar' as const,
        label: 'Stock',
        backgroundColor: '#E33A3A',
        data: stockData,
        stack: 'bar',
        pointStyle: 'rect',
        pointHitRadius: 0
      },
      {
        type: 'bar' as const,
        label: 'GIT',
        backgroundColor: '#52B735',
        data: gitData,
        stack: 'bar',
        pointStyle: 'rect',
        pointHitRadius: 0
      },
    ],
  };

  return chartData;
}


export const createSubmitMasterPayload = (master: any, action: string) => {
  return {
    id: parseInt(master.id),
    action: action,
    data: master.rowData
  }
}

export const addPrefixToObjectKeys = (obj: any, prefix: string) => {

  const newObj: any = {}

  Object.keys(obj).map((key) => {
    newObj[`${prefix + key}`] = obj[key]
  })
  return newObj
}

export const createConflictRowData = (conflicts: { conflictdetails: { oldData: any, requestedData: any }[], user: string }[], masterId: any): ColDef[] => {
  // console.log(conflicts)
  // console.log(TaskPendingAvoidColumnsMapper[masterId])
  const result: any[] = []
  conflicts.map((conflict) => {
    conflict.conflictdetails.map((conflictDetail, conflictIndex: number) => {
      const existingRowIndex = result.findIndex((row: any, index: number) => {
        let isDuplicate = false
        const primaryKeys: string[] = TaskPendingAvoidColumnsMapper[masterId]
        for (let i = 0; i < primaryKeys.length; i++) {

          if (row[primaryKeys[i]] === conflictDetail.requestedData[primaryKeys[i]]) {
            isDuplicate = true
          }
          else {
            isDuplicate = false
            break
          }
        }
        return isDuplicate
      })
      //console.log(existingRowIndex)

      if (existingRowIndex === -1) {
        result.push({ ...conflictDetail.requestedData, users: [{ user: conflict.user, data: conflictDetail.oldData }] })
      }
      else {
        result[existingRowIndex].users.push({ user: conflict.user, data: conflictDetail.oldData })
      }
    })
  })
  return result


}

export const createErrorRowData = (errorConflicts: { errorData: any[], errorType: string }[], masterId: any): ColDef[] => {
  //console.log(masterId)
  const result: any[] = []
  if (Array.isArray(errorConflicts)) {
    errorConflicts.map((currError: { errorData: any[], errorType: string }) => {
      currError.errorData.map((errorRowData: any) => {
        const existingRowIndex = result.findIndex((row: any) => {
          // const primaryKeys:string[] = TaskPendingAvoidColumnsMapper[masterId]
          // if(primaryKeys.length<3){
          //   return JSON.stringify(row)===JSON.stringify(errorRowData)
          //   // return row[primaryKeys[0]]===errorRowData[primaryKeys[0]]
          // }
          // console.log(row)
          let isDuplicate = false
          const primaryKeys: string[] = TaskPendingAvoidColumnsMapper[masterId]
          if (primaryKeys instanceof Array) {
            for (let i = 0; i < primaryKeys.length; i++) {
              if (row[primaryKeys[i]] === errorRowData[primaryKeys[i]]) {
                isDuplicate = true
              }
              else {
                isDuplicate = false
                break
              }
            }
          }
          return isDuplicate
          // const omittedResultEntry = _.omit(row,['error'])
          // return JSON.stringify(omittedResultEntry)===JSON.stringify(errorRowData)
        })


        if (existingRowIndex === -1) {
          result.push({
            ...errorRowData,
            error: " " + currError.errorType + " ."
          })
        }
        else {
          result[existingRowIndex].error += " " + currError.errorType + " ."
        }
      })
    })
  }
  //console.log(result)
  return result
}

export const navigateWithPrompt = (onRouteChange: () => void, url: any, state: any, resetState: any) => {

  if (!mdmRoutes.includes(url)) {
    if (state.activeMaster.id === 0) {
      onRouteChange();
    }
    else {
      if (confirm("Are you sure you want to leave this page?  All the Progress will be lost!")) {
        onRouteChange();
        resetState()
      }
    }
  }
  else {
    onRouteChange();
  }

}


export const FormatDateFunction =(dateStr:string)=>{
  const date = new Date(dateStr);

// Format to MM/DD/YYYY HH:mm:ss
const formattedDate = date.toLocaleString('en-US', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false
});
return formattedDate
}


export const createTaskPendingSubmitPayload = (rowData: any[], actionType: number, masterId: number): any[] => {
  const result: any[] = []

  rowData.forEach((item) => {
    // if((item.isModified  || actionType!==2 || masterId===6) ){
    // Create a new object to store modified key-value pairs
    const newItem: any = {};

    // Iterate through each key-value pair in the object
    Object.entries(item).forEach(([key, value]) => {
      // Check if the key starts with "Oldc"

      if (key === 'status') {
        return newItem[key] = value === "Approved" ? "3" : value === "Rejected" ? "4" : ""
      }

      if (actionType === 2) {
        if (key.startsWith("Old")) {
          // Skip keys with prefix "Oldc"
          return;
        }
        newItem[key.replace("New", "")] = value;
      }

      if (actionType === 1) {
        if (masterId === 13) {
          if (key.startsWith("Old")) {
            // Skip keys with prefix "Oldc"
            return;
          }
          newItem[key.replace("New", "")] = value;
        }
        else {
          newItem[key.replace("Add", "")] = value;
        }
      }

      if (actionType === 3) {

        newItem[key.replace("Delete", "")] = value;
      }

      // Remove the "Newc" prefix from the key and store the value in the new object

    });

    // Add the modified object to the result array
    const tempRow = _.omit({ ...newItem }, ['isModified', 'cmt'])
    result.push(tempRow);
    // }
  });

  return result
}


export const generateDailyDataGraphCell = (onOpenDailyDataGraph:any):ColDef=>{

  return {
    ...createIconColumn({id:'dailydatagraph',label:'',cellRenderer:'grapCellRenderer'}),
    cellRendererParams:{onOpenDailyDataGraph:onOpenDailyDataGraph},
    pinned: 'left',
    minWidth:45,
    resizable:false
  }
        // const dailyDataColDef = {...createIconColumn({id:'graph',label:'',cellRenderer:'grapCellRenderer'}),cellRendererParams:{onOpenDailyDataGraph:onOpenDailyDataGraph}}
}



export const createIconColumn = (params: any): ColDef => {

  const {
    id,
    label,
    cellRenderer
  } = params

  return {
    width: 40,
    minWidth: 40,
    colId: id,
    headerName: label,
    filter:false,
    cellRenderer: cellRenderer,
    floatingFilter: false,
    suppressColumnsToolPanel: false
  }
}

export const getCellDataType = (dataType: "Number"|"number"| "String" | "Boolean"): string => {
  if (dataType === 'Number') return "number"
  return 'text'
}

export const getCellFilter = (dataType: "Number"| "number" | "String" | "Boolean"): string => {
  if (dataType === 'number' || dataType==="Number") return "agNumberColumnFilter"
  // else if(dataType==='String') return 'agTextColumnFilter'
  // else if(dataType==='Boolean') return "agSetColumnFilter"
  return 'agMultiColumnFilter'
}


// export const mapColumnsWithConfigs = (CurrentState:any,initialState:ColDef[]) : ColDef[] =>{
//   // return CurrentState.map((col:any) => {
//   //   const matchedCol = initialState.find((initCol:any) => initCol.colId === col.colId);
//   //   return matchedCol ? { ...matchedCol, ...col, initialHide: col.hide !== undefined ? col.hide : false } : col;
//   // });
//   return CurrentState.map((col:any) => {
//   const matchedCol = initialState.find((initCol:any) => initCol.colId === col.colId);
//   return matchedCol ? { ...matchedCol, ...col } : col;
// });  
// }

// return CurrentState.map((col:any) => {
//   const matchedCol = initialState.find((initCol:any) => initCol.colId === col.colId);
//   return matchedCol ? { ...matchedCol, ...col } : col;
// });  

export const mapColumnsWithConfigs = (CurrentState: any, initialState: ColDef[]): ColDef[] => {
  return initialState.map((col: any) => {
    const matchedCol = CurrentState.find((initCol: any) => initCol.colId === col.colId);
    
    if (matchedCol) {
      const { hide, ...restCol } = col; // Exclude `hide` from col
      return { ...matchedCol, ...restCol, initialHide: hide !== undefined ? hide : matchedCol.initialHide };
    }

    return col;
  });
};


export const addCheckBoxColumn = ():ColDef =>{
  return  {
    field:'checkbox',
    colId:'checkbox',
    headerName:'',
    width:70,
    checkboxSelection:true,
    headerCheckboxSelection:true,
    headerCheckboxSelectionCurrentPageOnly:true,
    resizable:false,
    suppressMenu: true,
    maxWidth: 40,
    pinned: 'left',
    filter: false
  }
}

export const getRemarkRelatedColumns = (onOpenRemarkHistory: (params: any, e: any) => void) : ColDef[] => {
  return [
    {
      colId: 'remarks',
      field: 'remarks',
      headerName: 'Enter new remark',
      cellStyle:{
        backgroundColor: 'white',
        border: '1px solid #b9bdba',
        color: 'black',
        padding: '1px'
      },
      pinned: 'right',
      editable: true,
      minWidth:130,
      maxWidth:160,
      initialHide:false,
      lockPosition:'right',
      menuTabs: [] ,
      suppressMenu: true,
      resizable:false
    },
    {
      colId: 'rh',
      field: 'rh',
      headerName: 'Remark History',
      cellRenderer: 'remarksCellRenderer',
      cellRendererParams: {
        onClick: onOpenRemarkHistory
      },
      pinned: 'right',
      minWidth:120,
      maxWidth:120,
      initialHide:false,
      lockPosition:'right',
      menuTabs: [] ,
      suppressMenu: true,
      resizable:false
    }
  ]
}

export const filterParams =  {
  filters: [
    {
      filter: 'agTextColumnFilter',
      filterParams: {
        buttons: [ 'reset'],
      }
    },
    {
      filter: 'agSetColumnFilter',
      filterParams: {
        buttons: ['reset'],
      }
    },
  ]
}



export const CellRenderersMapping:any = {
  'DispatchPen':'colorDispatchRender',
  'TechPen':'colorTechCellRenderer',
  'EcoPen':'colorEcoCellRenderer',
  'TPen':'colorTechCellRenderer',
  'EPen':'colorEcoCellRenderer'
}

const aggridDefaultColumnProps = {
  sort: null,
  sortIndex: null,
  aggFunc: null,
  rowGroup: false,
  rowGroupIndex: null,
  pivot: false,
  pivotIndex: null,
  flex: undefined,
}

// function getCellRendererForKey(key:string) {
//   const renderer = CellRenderersMapping[key];
//   return renderer !== undefined ? renderer : 'string'; // If the renderer is undefined, return the key as string
// }


export const generateAndMapColumns = (reportName:string,fields:any ,includeRemarks:boolean,includeGraph:boolean,includeTags:boolean,onOpenSubmitRemark?:any,  onOpenRemarkHistory?:any, onOpenDailyDataGraph?:any) =>{
  
  if (!fields || fields.length < 1) {
    return []
  }
  let Columns:ColDef[] = [];

  Columns = fields.map((f:any,index:number)=>{
    if(f.Col_Code==='t' || f.Col_Code==='tags'){
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        cellRenderer: 'tagsCellRenderer',
        width: 100,
        pinned:null,
        // hide: !f.Visible,
        initialHide: !f.Visible,
        filter:true,
        filterParams: {
          buttons: ['reset'], // Adds Apply and Clear buttons
        },
        ...aggridDefaultColumnProps
      }
    }
    return {
      colId: f.Col_Code,
      field: f.Col_Code,
      headerName: f.Header,
      // hide: !f.Visible,
      initialHide: !f.Visible,
      cellRenderer: CellRenderersMapping[f.Col_Code] !== undefined ? CellRenderersMapping[f.Col_Code] : 'string' ,
      cellDataType: getCellDataType(f.DataType),
      filter: getCellFilter(f.DataType),
      minWidth:180,
      pinned:null,
      ...aggridDefaultColumnProps,
      filterParams:filterParams
    }
  })

  if(reportName==='ResearchInsight'){ // Add other reportName in || condition if checkbox is required
    Columns.push(addCheckBoxColumn())  /// required Checkbox for RI 
  }

  if(includeRemarks){ // If Remark is required in any reports then provide boolean as true
    Columns.unshift(...getRemarkRelatedColumns(onOpenRemarkHistory))
  }


  if(includeTags && ( reportName==='BPR' || reportName==='ResearchInsight' )){
    Columns.unshift({
      colId: 'tags',
      field: 'tags',
      headerName: "Tags",
      cellRenderer: 'tagsCellRenderer',
      width: 100,
      initialHide:false,
      filter:true,
      pinned:null,
      ...aggridDefaultColumnProps,
      filterParams: {
        buttons: ['reset'], // Adds Apply and Clear buttons
      },
    })
  }

  if(includeGraph){
    Columns.unshift(generateDailyDataGraphCell(onOpenDailyDataGraph))
  }


  return Columns
}

const createCommonTooltip = (seriesColor: string) => ({
  enabled: true,
  renderer: (params: any) => {
    const { datum, xKey, yKey, yName } = params;
    
    return `
      <div style="padding: 0; background: ${seriesColor}; border-radius: 4px; min-width: 120px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
        <div style="padding: 6px 12px; color: white; font-weight: 600; font-size: 13px;">
          ${yName}
        </div>
        <div style="padding: 8px 12px; background: white; border-radius: 0 0 4px 4px; color: #333; font-size: 13px;">
          ${datum[xKey]}: ${datum[yKey]}
        </div>
      </div>
    `;
  },
});

const colorNameMap: Record<string, string> = {
  "#fff": "White",
  "#000000": "Black",
  "#ED1C24": "Red",
  "#FFCB05": "Yellow",
  "#418D18": "Green",
  "#BCBCBC": "White",
  "#355FD3": "Blue",
};

const pieTooltip = {
  enabled: true,
  renderer: (params: any) => {
    const { datum, angleKey, fill, color } = params;
    const sliceColor = fill || color || datum.color || "#666666";
    const colorName = colorNameMap[sliceColor] || "Unknown";

    return `
      <div style="background: #6C696A; border-radius: 6px; overflow: hidden; text-align: center; min-width: 140px;">
        <div style="color: white; padding: 6px 10px; background-color: ${sliceColor}; font-weight: bold;">
          ${colorName}
        </div>
        <div style="color: black; padding: 8px 10px; background-color: #ede7e9ff;">
          ${datum[angleKey]}%
        </div>
      </div>
    `;
  },
};

export const generateChartOptions = (data: any, chartParams: any, isCategoryData?: string) => {
  const { series, palette, chartKey: keys, Labels, chartType, legend } = chartParams;

  const seriesMapped = series.map((obj: any, index: number) => {
    if (chartType === 'pie') {
      return { ...obj, tooltip: pieTooltip };
    }
    const seriesColor = palette?.fills?.[index] || '#666666';
    
    return { 
      ...obj, 
      tooltip: createCommonTooltip(seriesColor)
    };
  });

  if (data == null) return {};
  
  const options: AgChartOptions = {
    data: chartType === 'pie' ? addExtraColumnForLabels(data) : data.slice(0, 10),
    theme: {
      palette
    },
    series: seriesMapped,
    ...(chartType === 'pie' ? { legend: addLabelsToPieChart } : legend !== undefined ? { legend } : {}),
    ...(chartType != 'pie' ? createAxesForBarCharts(keys, Labels) : {}),
  };
  
  return options;
};

export const createAxesForBarCharts = (keys:any,Labels:any)=>{
  return {
    axes:[
      {
        type: "category",
        position: "bottom",
        keys:keys.Xaxis,
        title:{
          enabled:true,
          text:Labels.Xaxis,
          fontSize:10,
          fontFamily:'Roboto'
        },
        label:{
          formatter:(params:any)=>{
            if(Labels.Xaxis==='Date'){
              return new Date(params.value).toISOString().split('T')[0]
            }
            if(params.value.length > 10) return params.value.slice(0,10) + '...';
            return params.value;
          },
          fontSize:8,
          fontFamily:'Roboto'
        }
      },
      {
        type:'number',
        position:"left",
        keys:keys.Yaxis,
        title:{
          enabled:true,
          text:Labels.Yaxis,
          fontSize:10,
          fontFamily:'Roboto'
        },
        label:{
          fontSize:12
        }
      }
    ]
  }
}

export const addExtraColumnForLabels = (data:any)=>{
  const addedData = _.cloneDeep(data)
  if(addedData.length===0) return [];
  addedData.unshift({color:"custom",pre:-1, post:-2})
  return addedData;
}

export const addLabelsToPieChart = {
  enabled:true,
  item:{
    label:{
      formatter:(params: any) => {
        if(params.value == -1){
          return "PRE"
        }
        else if (params.value == -2){
          return "POST"
        }
        return params.value
      }
    }
  }
}

export const createTotalLegendForLineCharts = (data:any,key:string)=>{
  const totalSeriesData = data.reduce((acc: any, current: any) => {
    const existingDate = acc.find((d: any) => d.date === current.date);
    if (existingDate) {
      existingDate[key] += current[key];
    } else {
      acc.push({ date: current.date, [key]: current[key] }); // Fix applied here
    }
    return acc;
  }, []);
  /// return series
  return {
    type: 'line',
    xKey: 'date',
    yKey: key,
    yName: 'Total',
    data: totalSeriesData,
    stroke: '#BC3D81', /// change color as per requirement
    strokeWidth: 3,
    marker: {
        fill: '#BC3D81',
        size: 8,
        stroke: "#BC3D81",
        strokeWidth: 2,
    },
    visible:false
  }
}


export const categoryFormatter = (params:any)=>{
  if(params.value.value.length > 10) return params.value.toString().slice(0,10) + '...';
  return params.value;
}

export const generateGridSpecificChartFromChartProps = (options:any,downloadName:string):any =>{
  if(options===undefined){
    return null
  }
  return {
    palette:options?.theme?.palette,
    common: {
      legend: {
        position: "bottom",
      },
      title:{
        enabled:true,
        text:downloadName,
        fontSize:10
      },
      axes: {
        category: {
          title: {
            enabled: options.axes?.[0]?.title?.enabled ?? true,
            text: options.axes?.[0]?.title?.text ?? "",
            position: "bottom",
            fontSize: options.axes?.[0]?.title?.fontSize ?? 10,
            fontFamily: options.axes?.[0]?.title?.fontFamily ?? "Roboto",
          },
          label: {
            formatter:categoryFormatter,
            fontSize: options.axes?.[0]?.label?.fontSize ?? 8,
            fontFamily: options.axes?.[0]?.label?.fontFamily ?? "Roboto",
          },
        },
        number: {
          title: {
            enabled: options.axes?.[1]?.title?.enabled ?? true,
            text: options.axes?.[1]?.title?.text ?? "",
            position: "left",
            fontSize: options.axes?.[1]?.title?.fontSize ?? 10,
            fontFamily: options.axes?.[1]?.title?.fontFamily ?? "Roboto",
          },
        },
      },
    },
    bar: {
      series: {
        tooltip:{
          enabled:true,
          renderer:(params:any)=>{
              const datum = params.datum
              return {
                  title: `${params.yName}`,
                  content: `${datum[params.xKey].value}: ${datum[params.yKey]}`,
              }
          },
        }
      },
    },
  };
};


export const mapBPRFieldsToColDefs = (fields: BPRField[], onOpenSubmitRemark: (params: any, e: any) => void, onOpenRemarkHistory: (e: any, params: any) => void, onOpenDailyDataGraph: (params: any) => void): ColDef[] => {

  if (!fields || fields.length < 1) {
    return []
  }

  let result: ColDef[] = []

  const BPRSpecificColumns: ColDef[] = [
    {
      colId: 'remarks',
      field: 'remarks',
      headerName: 'Enter new remark',
      // cellRenderer: 'submitRemarkCellRenderer',
      // cellRendererParams: {
      //   onClick: onOpenSubmitRemark
      // },
      cellStyle:{
        backgroundColor: 'white',
        border: '1px solid #b9bdba',
        color: 'black',
        padding: '1px'
      },
      pinned: 'right',
      editable: true,
      minWidth:130,
      maxWidth:160,
      lockPosition:'right',
      menuTabs: [] ,
      suppressMenu: true,
      resizable:false
    },
    {
      colId: 'rh',
      field: 'rh',
      headerName: 'Remark History',
      cellRenderer: 'remarksCellRenderer',
      cellRendererParams: {
        onClick: onOpenRemarkHistory
      },
      pinned: 'right',
      minWidth:120,
      maxWidth:120,
      lockPosition:'right',
      menuTabs: [] ,
      suppressMenu: true,
      resizable:false
    }
  ]

  const tagsColDef: ColDef = {
    colId: 'tags',
    field: 'tags',
    headerName: "Tags",
    cellRenderer: 'tagsCellRenderer',
    width: 100,
    hide:false,
    filter:true,
    filterParams: {
      buttons: ['reset'], // Adds Apply and Clear buttons
    },
  }

  result = fields.map((f: BPRField) => {
    if (f.Col_Code === 'TechPen') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        hide: !f.Visible,
        cellRenderer: 'colorTechCellRenderer',
        // tooltipField: f.Col_Code,
        minWidth:180,
        cellDataType: getCellDataType(f.DataType),
        filter: getCellFilter(f.DataType),
        pinned:null,
        filterParams: {
          buttons: ['reset'], // Adds Apply and Clear buttons
          // excelMode: 'windows',
        },
      }
    }
    if (f.Col_Code === 'EcoPen') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        hide: !f.Visible,
        cellRenderer: 'colorEcoCellRenderer',
        // tooltipField: f.Col_Code,
        minWidth:180,
        cellDataType: getCellDataType(f.DataType),
        filter: getCellFilter(f.DataType),
        pinned:null,
        filterParams: {
          buttons: ['reset'], // Adds Apply and Clear buttons
          // excelMode: 'windows',
        },
      }
    }
    return {
      colId: f.Col_Code,
      field: f.Col_Code,
      headerName: f.Header,
      hide: !f.Visible,
      // tooltipField: f.Col_Code,
      minWidth:180,
      cellDataType: getCellDataType(f.DataType),
      // filter:true,
      pinned:null,
      filter: getCellFilter(f.DataType),
        filterParams: {
          filters: [
            {
              filter: 'agTextColumnFilter',
              filterParams: {
                buttons: [ 'reset'],
              }
            },
            {
              filter: 'agSetColumnFilter',
              filterParams: {
                buttons: ['reset'],
              }
            },
          ]
        },
      // filterParams: {
      //   buttons: ['reset','apply'], // Adds Apply and Clear buttons
      // },
    }
  })
  return [generateDailyDataGraphCell(onOpenDailyDataGraph), tagsColDef, ...result, ...BPRSpecificColumns]
}

export const MainMenuItemsCustomization = (params:any) => {
  const defaultItems = params.defaultItems;
  const conditionalItemsToRemove = ['remarks','rh']
  const itemsToRemove = ["columnChooser", "resetColumns"]; // Example items to remove
  if(conditionalItemsToRemove.includes(params.column.colId)){
    // itemsToRemove.push()
    itemsToRemove.push("pinSubMenu")
  }
  const modifiedItems = defaultItems.filter((item:any) => !itemsToRemove.includes(item));
   
  return modifiedItems;
}

export const mapBPRRowData = (rowData: Array<any>) => {
  //Logic is breaking, doesn't show the grey color on TechColor and EcoColor
  
  // return rowData.map((r) => {
  //   const tempRow = { ...r }
  //   if (r.Norm === 0) {
  //     tempRow.TechPen = null
  //     tempRow.EcoPen = null
  //     tempRow.EcoColor = null
  //     tempRow.TechColor = null
  //   }
    
  //   return tempRow
  // })
  
  return rowData
}



// export const updateCommonAttributes= (array1:any[], array2:any[], colId:string)=> {
//   // Create a new array to store the updated objects
//   const updatedArray:any[] = [];

//   // Iterate through array2 to find matching objects in array1 by colId
//   array2.forEach(obj2 => {
//     // Find the corresponding object in array1 by colId
//     const obj1 = array1.find(obj => obj[colId] === obj2[colId]);
    
//     if (obj1) {
//       // Create a copy of obj2 to update it without modifying the original
//       let updatedObj = { ...obj2 };
      
//       // Iterate over keys of obj1 (excluding colId) to find common attributes
//       Object.keys(obj1).forEach(key => {
//         if (key !== colId && key in obj2) {
//           // Replace common attributes in obj2 with those from obj1
//           updatedObj[key] = obj1[key];
//         }
//       });
      
//       // Push the updated obj2 to the result array
//       updatedArray.push(updatedObj);
//     } else {
//       // If no matching object is found, just push obj2 as it is
//       updatedArray.push(obj2);
//     }
//   });

//   // Return the updated array of objects
//   return updatedArray;
// }

export function convertStringNumToNumber(objects: any[]): any[] {
  return objects.map((obj) => {
    const updatedObj = { ...obj };

    // Check if 'actualStock' is a string and can be converted to a number
    if (updatedObj.sla2!==undefined && typeof updatedObj.sla2 === 'string') {
      const parsedNumber = parseFloat(updatedObj.sla2);
      if (!isNaN(parsedNumber)) {
        updatedObj.sla2 = parsedNumber;
      }
    }

    return updatedObj;
  });
}

export const updateCommonAttributes=(array1:any[], array2:any[], colId:string)=> {

  // Create a dictionary (map) of objects from array1 by colId
  const array1Dict:any = {};
  array1.forEach(obj => {
    array1Dict[obj[colId]] = obj;
  });

  // Iterate through array2 and update common attributes from array1
  array2.forEach(obj2 => {
    const obj1 = array1Dict[obj2[colId]]; // Find corresponding object in array1 by colId

    if (obj1) {
      // For the common object, find common keys (excluding colId)
      Object.keys(obj1).forEach(key => {
        if (key !== colId && key in obj2) {
          // Replace common attributes in obj2 with those from obj1
          obj2[key] = obj1[key];
        }
      });

      if("hide" in obj1){
        obj2['hide']=obj1['hide']
      }
    }
  });

  // Return the updated array2
  return array2;
}


export const mapResearchInsightsFieldsToColDefs = (fields: BPRField[], onOpenDailyDataGraph: any): ColDef[] => {

  if (!fields || fields.length < 1) {
    return []
  }

  let result: ColDef[] = []

  const checkboxColDef: ColDef = {
    field: 'checkbox',
    colId: 'checkbox',
    headerName: '',
    floatingFilter: false,
    checkboxSelection: true,
    headerCheckboxSelection: true,
    headerCheckboxSelectionCurrentPageOnly: true,
    width: 40,
    suppressColumnsToolPanel: true,
    filter: false,
  }


  const tagsColDef: ColDef = {
    colId: 'tags',
    field: 'tags',
    headerName: "Tags",
    cellRenderer: 'tagsCellRenderer',
    filter: "agMultiColumnFilter",
    width: 100
  }

  result = fields.map((f: BPRField) => {
    if (f.Col_Code === 'TechPen') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        hide: !f.Visible,
        cellRenderer: 'colorTechCellRenderer',
        cellStyle: {
          'min-width': 180,
        },
        cellDataType: getCellDataType(f.DataType),
        filter: getCellFilter(f.DataType)
      }
    }
    if (f.Col_Code === 'EcoPen') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        hide: !f.Visible,
        cellRenderer: 'colorEcoCellRenderer',
        cellStyle: {
          'min-width': 180,
        },
        cellDataType: getCellDataType(f.DataType),
        filter: getCellFilter(f.DataType)
      }
    }
    return {
      colId: f.Col_Code,
      field: f.Col_Code,
      headerName: f.Header,
      hide: !f.Visible,
      cellStyle: {
        'min-width': 180,
      },
      cellDataType: getCellDataType(f.DataType),
      filter: getCellFilter(f.DataType)
    }
  })
  return [checkboxColDef, { ...createIconColumn({ id: 'dailydatagraph', label: '', cellRenderer: 'grapCellRenderer' }), cellRendererParams: { onOpenDailyDataGraph: onOpenDailyDataGraph } }, tagsColDef, ...result]
}

export const mapBORFieldsToColDefs = (fields:UiConfigField[], onOpenSubmitRemark: (params: any, e: any) => void, onOpenRemarkHistory: (e: any, params: any) => void, onOpenDailyDataGraph: (params: any) => void): ColDef[] => {

  if (!fields || fields.length < 1) {
    return []
  }

  let result: ColDef[] = []

  const BORSpecificColumns: ColDef[] = [
    {
      colId:'remarks',
      field:'remarks',
      headerName:'Enter new remark',
            // cellRenderer: 'submitRemarkCellRenderer',
      // cellRendererParams: {
      //   onClick: onOpenSubmitRemark
      // },
      cellStyle:{
        backgroundColor: 'white',
        border: '1px solid #b9bdba',
        color: 'black',
        padding: '1px'
      },
     pinned: 'right',
     editable: true,
     minWidth:130,
     maxWidth:160,
     lockPosition:'right',
     menuTabs: [] ,
     suppressMenu: true,
     resizable:false
    },
    {
      colId:'rh',
      field:'rh',
      headerName:'Remark History',
      cellRenderer:'remarksCellRenderer',
      cellRendererParams:{
        onClick:onOpenRemarkHistory
       },
       pinned: 'right',
       minWidth:120,
       maxWidth:120,
       lockPosition:'right',
       menuTabs: [] ,
       suppressMenu: true,
       resizable:false
    }
  ]



  result = fields.map((f: UiConfigField) => {


    if (f.Col_Code === 'DispatchPen') {
      return {
        colId: f.Col_Code,
        field: f.Col_Code,
        headerName: f.Header,
        hide: !f.Visible,
        floatingFilter: true,
        cellRenderer: 'colorDispatchCellRenderer',
        filter: getCellFilter(f.DataType),
        cellDataType: getCellDataType(f.DataType)
      }
    }
    return {
      colId: f.Col_Code,
      field: f.Col_Code,
      headerName: f.Header,
      hide: !f.Visible,
      floatingFilter: true,
      filter: getCellFilter(f.DataType),
      cellDataType: getCellDataType(f.DataType)
    }
  })
  //return [...result, ...BORSpecificColumns]
  return [generateDailyDataGraphCell(onOpenDailyDataGraph), ...result, ...BORSpecificColumns]
}

export const BPRColorMapper = (color: string): { bg: string, text: string } => {

  switch (color) {
    case "White":
      return {
        "bg": "white",
        "text": "black"
      }
    case "Yellow":
      return {
        "bg": "#EBBF2B",
        "text": "white"
      }
    case "Green":
      return {
        "bg": "#418D18",
        "text": "white"
      }
    case "Red":
      return {
        "bg": "#F04D4D",
        "text": "white"
      }
    case "Black":
      return {
        "bg": "#000000",
        "text": "white"
      }
    case "Blue":
      return {
        "bg": "blue",
        "text": "white"
      }
    case "default":
      return {
        'bg':"#9c9ce7",
        "text": "white"
      }
    
    case "disabled":
      return{
        "bg":"#88888a",
        "text": "white"
      }

    case "selected":
     return{
      "bg":"#d45293",
      "text": "white"
     }
    
    default:
      return {
        "bg": "#B2B2B2",
        "text": "white"
      }
  }
}

export const mapBTRRowData = (rows: Array<any>, horizon: number): Array<any> => {
  const columnsNotBeConverted = ['SKUCode','SKUDescription','Whcode','WhCode','LocationName','pc','pn']
  return rows.map((r) => {
    const transformedRow = Object.keys(r).reduce((acc, key) => {
      let value = r[key];
      if(value===null){
        value = "";
      }
      if(columnsNotBeConverted.includes(key)){
        acc[key]=value+"";
      }else if (typeof value === 'string' && !isNaN(parseFloat(value))) {
        acc[key] = parseFloat(value);
      } else {
        acc[key] = value;
      }
      return acc;
    }, {} as any);
 
 
    const NewCategoryString = transformedRow.Category;
    const tempRow = { ...transformedRow, Category: NewCategoryString };
    let tempAvailabilty = 0;
    let nonBlackCount = 0;
    let EmptyCount = 0;
    for (let index = 90; index > 90 - horizon; index--) {
      if (tempRow[`D${index}`]!== "" && parseInt(tempRow[`D${index}`]) < 100) {
        nonBlackCount = nonBlackCount + 1;
      }
      if (tempRow[`D${index}`]=== "") {
        EmptyCount = EmptyCount + 1;
      }
    }

    tempAvailabilty = parseFloat(((nonBlackCount / (horizon-EmptyCount)) * 100).toFixed(2))
    return {
      ...tempRow,
      Availability: tempAvailabilty
    }
  })
 
}

export const mapBTRRowDataToColDefs = (row: any, dateMapper: any, horizon: number, pinCatergory: boolean, excludeColumns?: Array<string>, onOpenDailyDataGraph?:any): Array<ColDef> => {
  // const graphCellRenderer:ColDef={
  //   field:'graph',
  //   colId:'graph',
  //   headerName:'',
  //   cellRenderer:'graphCellRenderer',
  //   cellRendererParams:{
  //     onShowChart:onShowChart
  //   },
  //   cellStyle:{
  //     'zoom':'0.7'
  //   },
  //   minWidth:60,
  //   // cellStyle:{
  //   //   'max-width':100,
  //   //   'margin-left':20,
  //   //   'margin-right':40
  //   // },
  //   flex: 1
  // }

  const specificColumns:any =[
    {
      colId:'dailydatagraph',
      field:'',
      headerName:'',
      width:40,
      pinned: 'left',
      floatingFilter:false,
      position:0,
      tooltipField:"DailyDataGraph",
      cellRenderer:'grapCellRenderer',
      cellRendererParams:{
        onOpenDailyDataGraph:onOpenDailyDataGraph
      },
    }
  ]


  let result = Object.keys(row).map((key: string): ColDef => {

    if (key.startsWith('D')) {
      return {
        field: key,
        colId: key,
        headerName: format(dateMapper[key], 'PP'),
        cellRenderer: 'colorCellRenderer',
        cellRendererParams: (params: any) => {
          return {
            colorValue: params.data[key]
          }
        },

        ...BTRDefaultColDefs,
        minWidth: 100
      }
    }

    if (key === 'Tags') {
      return {
        field: key,
        colId: key,
        headerName: key,
        cellRenderer: 'tagsCellRenderer',

        ...BTRDefaultColDefs
      }
    }
    if (key == 'age') {
      return {
        field: key,
        colId: key,
        headerName: 'Age',
        ...BTRDefaultColDefs
      }
    }
    if (key == 'pc') {
      return {
        field:key,
        colId:key,
        headerName:'Parent Code',
        ...BTRDefaultColDefs
      }
    }
    if (key == 'pn') {
      return {
        field:key,
        colId:key,
        headerName:'Parent Name',
        ...BTRDefaultColDefs
      }
    }
    
    if(key=='wc'){
      return {
        field:key,
        colId:key,
        headerName:'White in 30 days',
        ...BTRDefaultColDefs
      }
    }
    if(key=='bc'){
      return {
        field:key,
        colId:key,
        headerName:'Black in 30 days',
        ...BTRDefaultColDefs
      }
    }
     if(key=='blc'){
      return {
        field:key,
        colId:key,
        headerName:'Blue in 30 days',
        ...BTRDefaultColDefs
      }
    }
     if(key=='rc'){
      return {
        field:key,
        colId:key,
        headerName:'Red in 30 days',
        ...BTRDefaultColDefs
      }
    }
     if(key=='yc'){
      return {
        field:key,
        colId:key,
        headerName:'Yellow in 30 days',
        ...BTRDefaultColDefs
      }
      
    }
     if(key=='gc'){
      return {
        field:key,
        colId:key,
        headerName:'Green in 30 days',
        ...BTRDefaultColDefs
      }
    }

    if (key == 'wc') {
      return {
        field: key,
        colId: key,
        headerName: 'WhiteCount',
        ...BTRDefaultColDefs
      }
    }
    if (key == 'bc') {
      return {
        field: key,
        colId: key,
        headerName: 'BlackCount',
        ...BTRDefaultColDefs
      }
    }
    if (key == 'blc') {
      return {
        field: key,
        colId: key,
        headerName: 'BlueCount',
        ...BTRDefaultColDefs
      }
    }
    if (key == 'rc') {
      return {
        field: key,
        colId: key,
        headerName: 'RedCount',
        ...BTRDefaultColDefs
      }
    }
    if (key == 'yc') {
      return {
        field: key,
        colId: key,
        headerName: 'YellowCount',
        ...BTRDefaultColDefs
      }

    }
    if (key == 'gc') {
      return {
        field: key,
        colId: key,
        headerName: 'GreenCount',
        ...BTRDefaultColDefs
      }
    }

    if (key === 'Availability') {
      return {
        field: key,
        colId: key,
        headerName: key,
        cellRenderer: 'availabilityCellRenderer',
        tooltipField: key,
        tooltipComponent: 'availabilityToolTip',

        ...BTRDefaultColDefs
      }
    }

    if (key === 'Category') {
      return {
        field: key,
        colId: key,
        headerName: key,
        cellRenderer: 'categoryCellRenderer',
        tooltipField: key,
        tooltipComponent: 'categoryToolTip',
        pinned: pinCatergory ? 'left' : false,
        ...BTRDefaultColDefs,
        width: 70
      }
    }

    return {
      field: key,
      colId: key,
      headerName: key,
      ...BTRDefaultColDefs
    }
  })
  // if(onShowChart)result = [graphCellRenderer,...result]
  result = result.filter((r) => (!r.colId?.startsWith('D')) || (r.colId.startsWith('D') && parseInt(r.colId.slice(1)) > 90 - horizon))
 
  if (excludeColumns) result = result.filter((r) => r.colId && !excludeColumns.includes(r.colId))
  return [...specificColumns,...result]

}

export const mapDBMFieldsToColDefs = (fields: DBMField[], onOpenDailyDataGraph: any, afterSleepCallBack: () => void): ColDef[] => {


  if (!fields || fields.length < 1) {
    return []
  }

  fields.sort((a: DBMField, b: DBMField) => a.Col_Position - b.Col_Position);
  // console.log(fields);

  let result: ColDef[] = []


  const DBMTickColumn: ColDef = {
    field: 'checkbox',
    colId: 'checkbox',
    headerName: '',
    floatingFilter: false,
    checkboxSelection: true,
    headerCheckboxSelectionCurrentPageOnly: true,
    width: 45,
    pinned: 'left',
    lockPosition: 'left',
    initialHide:false,
    suppressMenu:true
  }

  const DBMGraphColumn: ColDef[] = [
    {
      colId: 'dailydatagraph',
      field: '',
      headerName: '',
      width: 60,
      minWidth:60,
      maxWidth:70,
      lockPosition: true,
      floatingFilter: false,
      tooltipField: "DailyDataGraph",
      cellRenderer: 'grapCellRenderer',
      cellRendererParams: {
        onOpenDailyDataGraph: onOpenDailyDataGraph
      },
      initialHide:false,
      pinned:'left',
      suppressMenu:true
    }
  ]

  const DBMSleepColumn: ColDef[] = [
    {
      colId: 'sleep',
      headerName: 'Sleep',
      lockPosition: true,
      cellRenderer: 'sleepCellRenderer',
      cellRendererParams: {
        callBack: afterSleepCallBack
      },
      floatingFilter: false,
      minWidth: 100,
      maxWidth: 100,
      initialHide:false,
      pinned:'left',
      suppressMenu:true
    }
  ]

  const SuggestionCategory: ColDef = {
    headerName: '',
    lockPosition: true,
    cellRenderer: 'suggestionCategoryCellRenderer',
    floatingFilter: false,
    minWidth: 30,
    maxWidth: 30,
    initialHide:false,
    pinned:'left',
    suppressMenu:true
  }



  result = fields.map((f: DBMField) => {
    return {
      colId: f.Col_Code,
      field: f.Col_Code,
      headerName: f.Header,
      hide: !f.Visible,
      cellDataType: getCellDataType(f.DataType),
      filter: getCellFilter(f.DataType)
    }
  })

  const additionalColumns: ColDef[] = [
    {
      colId: 'OldNormValue',
      field: 'OldNormValue',
      headerName: 'Old Norm',
      hide: false,
      cellDataType: getCellDataType('Number'),
      filter: getCellFilter('Number')
    },
    {
      colId: 'NewNormValue',
      field: 'NewNormValue',
      headerName: 'New Norm',
      hide: false,
      cellDataType: getCellDataType('Number'),
      filter: getCellFilter("Number")
    },
    {
      colId: 'Comment',
      field: 'Comment',
      headerName: 'Reason',
      hide: false,
      cellDataType: getCellDataType("String"),
      filter: getCellFilter("String")
    }
  ]

  const insertPosition = 4;
  result.splice(insertPosition, 0, ...additionalColumns);

  return [DBMTickColumn, ...DBMGraphColumn, { ...SuggestionCategory }, ...DBMSleepColumn, ...result]

}

export const mapInTransitWhereAboutsRowData = (rowData: Array<any>): Array<any> => {
  if (!rowData || !Array.isArray(rowData)) return []
  // PhysicalInventoryColor
  return rowData.map((r: any) => {
    if (!r.skuDetails || r.skuDetails.length < 1) return r
    let legalCount = 0
    const colorArrayMap: any = {
      "Black": 0,
      "Red": 0,
      "Yellow": 0,
      "Green": 0,
      "White": 0
    }
    r.skuDetails.forEach((sd: any) => {
      if (sd.PhysicalInventoryColor) {
        colorArrayMap[sd.PhysicalInventoryColor] = colorArrayMap[sd.PhysicalInventoryColor] + 1
        legalCount += 1
      }

    })
    return {
      ...r,
      on_hand_penetration: colorArrayMap,
      count: legalCount
    }
  })

}

export const mapSubmitRemarkData = (row: any): any => {
  return {


    OrderNo: row.OrderNo,
    SKUCode: row.SKUCode,
    WhCode: row.WhCode,
    ParentWHCode: row.SenderLocation,
    Remarks: row.action || "",
    CurrentLocation: row.CurrentLoc,
    ETA: row.ETA.replace(/-/g, '/')


  }
}


export const convertToInt = (data: any, keys: string[]) => {
  return data.map((row: any) => {
    const tempObj: any = {};
    Object.keys(row).forEach((key: string) => {
      const value = parseFloat(row[key])
      if (keys.includes(key) && !isNaN(value)) {
        tempObj[key] = value
      }
      else {
        tempObj[key] = row[key];
      }
    })
    return { ...tempObj }
  })
}

export const getColumnsForExcelExport = (columns: Array<ColDef>): any => {
  const defaultColumnsToExclude = ['checkbox', 'dailydatagraph', 'sleep', 'tags', 'rh', 'remarks', 'AgeingOrder', 't']
  return columns.filter((c: ColDef) => (c.colId !== undefined && !defaultColumnsToExclude.includes(c.colId))).map((c) => (c.colId && c.colId))

}

export const getBPRViewTableHeaderFilterOptions = (dataType: string | undefined): Array<{ value: string, label: string }> => {
  if (dataType === 'number') {
    return BPRViewTableHeaderFilterNumberoptions
  }

  return BPRViewTableHeaderFilterStringoptions
}

export const performStringOpertionsForBPRViewTableFilter = (reference: string, value: string, operator: BPRViewTableFilterStringOperator): boolean => {
  //String operations
  switch (operator) {
    case 'contains':
      return reference.includes(value)
    case 'doesNotContain':
      return !reference.includes(value)
    case 'equals':
      return reference === value
    case 'doesNotEqual':
      return reference !== value
    default:
      return false
  }

}

export const performNumericalOpertionsForBPRViewTableFilter = (num1: number, num2: number, operator: BPRViewTableFilterNumericalOperator): boolean => {

  switch (operator) {
    case 'equals':
      return num1 === num2
    case 'doesNotEqual':
      return num1 !== num2
    case 'greaterThan':
      return num2 < num1
    case 'lessThan':
      return num2 > num1
    default:
      return false
  }

}

export const getFiltersArrayFromColDefs = (colDefs: Array<BPRViewTableColDef>): Array<any> => {
  return colDefs.filter((c) => c.filter).map((f) => ({ colId: f.colId, filterValue: '', dataType: f.dataType, query: null }))
}

export const storeCellColors: Record<string, { color: string; backgroundColor: string, border: string }> = {
  surplus: {
    color: '#585757',
    backgroundColor: '#fafafaff',
    border: '#d0d6ceff'
  },
  complete: {
    color: '#306A0F',
    backgroundColor: '#f7fff2ff',
    border: '#dfedd8ff'
  },
  incomplete: {
    color: '#816F08',
    backgroundColor: '#fffcedff',
    border: '#faf7deff'
  },
  'very-incomplete': {
    color: '#C61C1C',
    backgroundColor: '#fff2f2ff',
    border: '#e8c1beff'
  },
  default: {
    color: '#585757',
    backgroundColor: '#EBE5E5',
    border: '#d0d6ceff'
  }
};

export const floatingStoreColors: Record<string, { color: string; backgroundColor: string, border: string }> = {
  surplus: {
    color: '#585757',
    backgroundColor: '#fafafaff',
    border: '#d0d6ceff'
  },
  complete: {
    color: '#306A0F',
    backgroundColor: '#f7fff2ff',
    border: '#dfedd8ff'
  },
  incomplete: {
    color: '#816F08',
    backgroundColor: '#fffcedff',
    border: '#faf7deff'
  },
  'very-incomplete': {
    color: '#C61C1C',
    backgroundColor: '#fff2f2ff',
    border: '#e8c1beff'
  },
  default: {
    color: '#585757',
    backgroundColor: '#EBE5E5',
    border: '#d0d6ceff'
  }
};


export const getMCGridStoreImgSrc = (status: string): string => {
  if ('surplus' === status) return '/assets/img/VectorFLOW/BPR/mc-grid-surplus.svg'
  if ('incomplete' === status) return '/assets/img/VectorFLOW/BPR/mc-grid-deficit-incomplete.svg'
  return '/assets/img/VectorFLOW/BPR/mc-grid-deficit-very-incomplete.svg'
}

export const getMCGridStoreIconColor = (status: string): string => {
  if ('very-incomplete' === status) return '#F8416C'
  if ('incomplete' === status) return '#ED8D3A'
  return 'rgb(105, 105, 105)'
}


export const getProductAndLocationHeirarchiesFromEnv = (column: any, extraProperties: any, PRODUCT_PERMISSION_L1?: any, PRODUCT_PERMISSION_L2?: any, PRODUCT_PERMISSION_L3?: any, LOCATION_PERMISSION_L1?: any, LOCATION_PERMISSION_L2?: any, LOCATION_PERMISSION_L3?: any) => {
  


  if (column.colCode === 'sl1') {
    return {
      field: column['colCode'],
      colId: column['colCode'],
      headerName: PRODUCT_PERMISSION_L1,
      ...extraProperties
    }
  }
  if (column.colCode === 'sl2') {
    return {
      field: column['colCode'],
      colId: column['colCode'],
      headerName: PRODUCT_PERMISSION_L2,
      ...extraProperties
    }
  }
  if (column.colCode === 'sl3') {
    return {
      field: column['colCode'],
      colId: column['colCode'],
      headerName: PRODUCT_PERMISSION_L3,
      ...extraProperties
    }
  }
  if (column.colCode === 'll1') {
    return {
      field: column['colCode'],
      colId: column['colCode'],
      headerName: LOCATION_PERMISSION_L1,
      ...extraProperties
    }
  }
  if (column.colCode === 'll2') {
    return {
      field: column['colCode'],
      colId: column['colCode'],
      headerName: LOCATION_PERMISSION_L2,
      ...extraProperties
    }
  }

  if (column.colCode === 'll3') {
    return {
      field: column['colCode'],
      colId: column['colCode'],
      headerName: LOCATION_PERMISSION_L3,
      ...extraProperties
    }
  }

  return undefined;
}




export const convertUiConfigToOptions = (data:any) => {
  return data?.map((column:any)=>{
    return {
      value:column.Col_Code,
      label:column.Header
    }
  })
}


export const handleDownloadVFReports = async (payload:{name:string,filters:any}) => {

  try {
    const {name} = payload
    const response = await fetch(`${process.env.REACT_APP_API_HOST}/download-excel`, {
      headers: {
        'Content-Type': 'application/json'
      },
      method:"post",
      credentials:"include",
      body:JSON.stringify(payload)
    })  
    if(!response.ok){
      notifyError("Error while downloading")
      return false; 
    }else{
    // Convert response to blob object
    const blob = await response.blob()

    // Create download URL for blob object
    const url = URL.createObjectURL(blob)
  
    // Trigger download
    const link = document.createElement('a')
    link.href = url
    if(name.length!==0){
      link.setAttribute('download', `${name}`)
    }else{
      link.setAttribute('download', `ReportFile.csv`)
    }
    document.body.appendChild(link)
    link.click()
    // Clean up download URL
    URL.revokeObjectURL(url);
    
  }
  } catch (error:any) {
    notifyError('Error while downloading');
    return false;
  }
 
}
export const mapProcPlanningFieldsToColDefs = (fields: ColumnHeaderConfig[]): ColDef[] => {

  if (!fields || fields.length < 1) {
    return [];
  }
  let result: ColDef[] = [];
  const PPColumns: ColDef[] = [
  ]

  result = fields.map((f: ColumnHeaderConfig) => {
    if (f.jf === 'ic') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: 'agGroupCellRenderer',
        initialWidth: 20,
      }
    }
    if (f.jf === 'cp') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: "coloPriority",
        tooltipValueGetter: (params: any) => {
          const cpData = params.data.cp[0];
          const keysToPrint = ["B", "R", "Y", "G", "W", "Bl"];
          let tooltipText = '';
          keysToPrint.forEach((key) => {
            if (Object.prototype.hasOwnProperty.call(cpData, key)) {
              if (tooltipText !== '') {
                tooltipText += ' | ';
              }
              tooltipText += `${key}: ${cpData[key]}`;
            }
          });
          return tooltipText;
        },
        tooltipComponent: "availabilityToolTip",
        initialWidth: 200, //160
        autoHeaderHeight: true,
        wrapHeaderText: true,
      }
    }
    if (f.jf === 'eas') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: "inputbox",
        editable: true,
        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200, //160
        filter: 'agMultiColumnFilter',
        floatingFilter: true,
        cellStyle: {
          backgroundColor: 'white',
          border: '1px solid #b9bdba',
          color: 'black',
          padding: '1px',
        },
      }
    }

    if (f.jf === "rmd") {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        tooltipField: f.jf,
        initialWidth: 300, //160
        filter: 'agMultiColumnFilter',
        floatingFilter: true,
      }
    }

    if (f.jf === "rm") {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        tooltipField: f.jf,
        initialWidth: 200, //160
        filter: 'agMultiColumnFilter',
        floatingFilter: true,
      }
    }
    return {
      colId: f.jf,
      [f.jf]: f.val,
      field: f.jf,
      headerName: f.hdr,
      hide: !f.vs,
      autoHeaderHeight: true,
      wrapHeaderText: true,
      initialWidth: 200, //160
      filter: 'agMultiColumnFilter',
      floatingFilter: true,
    }
  })

  return [...result, ...PPColumns];
};
export const mapProcPlanningChildrenFieldsToColDefs = (fields: ColumnHeaderConfig[]): ColDef[] => {

  if (!fields || fields.length < 1) {
    return [];
  }
  let result: ColDef[] = [];
  const PPChildrenColumns: ColDef[] = []
  result = fields.map((f: ColumnHeaderConfig) => {
    if (f.jf === 'clr') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: 'coloPriorityOfBall',
        filter: 'agMultiColumnFilter',
        floatingFilter: false,
        initialWidth: 20,
        headerClass: "child-header",
        autoHeaderHeight: true,
        wrapHeaderText: true,
      }
    }
    if (f.jf === 'ord') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        filter: 'agMultiColumnFilter',
        floatingFilter: false,
        hide: !f.vs,
        headerClass: "child-header",
        // autoHeaderHeight: true,
        // wrapHeaderText: true,
        initialWidth: 300,
      }
    }
    return {
      colId: f.jf,
      [f.jf]: f.val,
      field: f.jf,
      headerName: f.hdr,
      hide: !f.vs,
      filter: 'agMultiColumnFilter',
      floatingFilter: false,
      headerClass: "child-header",
      autoHeaderHeight: true,
      wrapHeaderText: true,
    }
  })

  return [...result, ...PPChildrenColumns];
};

export const mapSimulateProcPlanningFieldsToColDefs = (fields: ColumnHeaderConfig[]): ColDef[] => {

  if (!fields || fields.length < 1) {
    return [];
  }
  let result: ColDef[] = [];
  const PPColumns: ColDef[] = [
  ]
  result = fields.map((f: ColumnHeaderConfig) => {
    if (f.jf === 'ic') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,

        cellRenderer: 'agGroupCellRenderer',
        cellStyle: {
          width: 50,
          maxWidth: 50,
        },
        initialWidth: 40,
      }
    }
    if (f.jf === 'cp') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: "colorCellRenderer",
        initialWidth: 200,//160
        autoHeaderHeight: true,
        wrapHeaderText: true,
      }
    }
    if (f.jf === 'fka') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: "avlCellRenderer",
        tooltipComponent: 'availabilityToolTip',
        tooltipValueGetter: (params: any) => {
          const oq = params.data.oq;
          const fka = params.data.fka;
          return `${fka}/${oq} kits can be manufactured`;
        },
        initialWidth: 200,//160
        autoHeaderHeight: true,
        wrapHeaderText: true,
        filter: 'agMultiColumnFilter',
        floatingFilter: true,
      }
    }
    if (f.jf === 'item') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        tooltipField: f.jf,
        initialWidth: 200,//160
        filter: 'agMultiColumnFilter',
        floatingFilter: true,
      }
    }
    if (f.jf === 'id') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        tooltipField: f.jf,
        initialWidth: 300,//160
        filter: 'agMultiColumnFilter',
        floatingFilter: true,
      }
    }
    return {
      colId: f.jf,
      [f.jf]: f.val,
      field: f.jf,
      headerName: f.hdr,
      hide: !f.vs,
      autoHeaderHeight: true,
      wrapHeaderText: true,
      initialWidth: 200,//160
      filter: 'agMultiColumnFilter',
      floatingFilter: true,
      // aggFunc: "sum"
    }
  })

  return [...result, ...PPColumns];
};

export const mapSimulateHedaerChildrenFieldsToColDefs = (fields: ColumnHeaderConfig[]): ColDef[] => {

  if (!fields || fields.length < 1) {
    return [];
  }
  let result: ColDef[] = [];
  const SimChildrenColumns: ColDef[] = [
  ]
  result = fields.map((f: ColumnHeaderConfig) => {
    if (f.jf === 'clr') {
      return {
        colId: f.jf,
        field: f.jf,
        maxWidth: 50,
        headerName: f.hdr,
        hide: !f.vs,
        floatingFilter: false,
        cellRenderer: 'coloPriorityOfBall',

        initialWidth: 20,
        headerClass: "simchild-header",
      }
    }
    if (f.jf === 'rm') {
      return {
        colId: f.jf,
        field: f.jf,
        filter: 'agMultiColumnFilter',
        floatingFilter: false,
        headerName: f.hdr,
        hide: !f.vs,
        headerClass: "simchild-header",
      }
    }
    if (f.jf === 'rmd') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        filter: 'agMultiColumnFilter',
        floatingFilter: false,
        hide: !f.vs,
        initialWidth: 300,
        headerClass: "simchild-header",
      }
    }
    return {
      colId: f.jf,
      [f.jf]: f.val,
      field: f.jf,
      headerName: f.hdr,
      filter: "agMultiColumnFilter",
      floatingFilter: false,
      hide: !f.vs,
      headerClass: "simchild-header",
    }
  })

  return [...result, ...SimChildrenColumns];
};

export const mapMaterialCoverageFieldsToColDefs = (fields: ColumnHeaderConfig[]): ColDef[] => {

  if (!fields || fields.length < 1) {
    return [];
  }
  let result: ColDef[] = [];
  const PPColumns: ColDef[] = [
  ]

  result = fields.map((f: ColumnHeaderConfig) => {
    if (f.jf === "ic") {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: "customGroupCellRenderer",
        initialWidth: 80,
      };
    }
    if (f.jf === 'cp') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: "colorCellRenderer",
        initialWidth: 200,//160
        autoHeaderHeight: true,
        wrapHeaderText: true,
      }
    }
    if (f.jf === 'fka') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: "avlCellRenderer",
        tooltipComponent: 'availabilityToolTip',
        tooltipValueGetter: (params: any) => {
          const oq = params.data.oq;
          const fka = params.data.fka;
          return `${fka}/${oq} kits can be manufactured`;
        },
        initialWidth: 200,//160
        autoHeaderHeight: true,
        wrapHeaderText: true,
        filter: 'agMultiColumnFilter',
        floatingFilter: true,
      }
    }
    return {
      colId: f.jf,
      [f.jf]: f.val,
      field: f.jf,
      headerName: f.hdr,
      hide: !f.vs,
      autoHeaderHeight: true,
      wrapHeaderText: true,
      initialWidth: 200, //160
      filter: 'agMultiColumnFilter',
      floatingFilter: true,
    }
  })

  return [...result, ...PPColumns];
};
export const mapMaterialFieldsToColDefs = (fields: ColumnHeaderConfig[]): ColDef[] => {

  if (!fields || fields.length < 1) {
    return [];
  }
  let result: ColDef[] = [];
  const PPColumns: ColDef[] = [
  ]

  result = fields.map((f: ColumnHeaderConfig) => {

    if (f.jf === 'cp') {
      return {
        colId: f.jf,
        field: f.jf,
        headerName: f.hdr,
        hide: !f.vs,
        cellRenderer: "coloPriority",
        tooltipValueGetter: (params: any) => {
          const cpData = params.data.cp[0];
          const keysToPrint = ["B", "R", "Y", "G"];
          let tooltipText = '';
          keysToPrint.forEach((key) => {
            if (Object.prototype.hasOwnProperty.call(cpData, key)) {
              if (tooltipText !== '') {
                tooltipText += ' | ';
              }
              tooltipText += `${key}: ${cpData[key]}`;
            }
          });
          return tooltipText;
        },
        tooltipComponent: "availabilityToolTip",
        initialWidth: 400, //160
        autoHeaderHeight: true,
        wrapHeaderText: true,
      }
    }

    return {
      colId: f.jf,
      [f.jf]: f.val,
      field: f.jf,
      headerName: f.hdr,
      hide: !f.vs,
      autoHeaderHeight: true,
      wrapHeaderText: true,
      initialWidth: 400, //160
      filter: 'agMultiColumnFilter',
      floatingFilter: true,
    }
  })

  return [...result, ...PPColumns];
};

// Generate ColumnDefination from UIConfig
// ===================================================================================================
export function mergeObjects(target: any, ...sources: any) {
  sources.forEach((source: any) => {
    Object.keys(source).forEach(key => {
      if (source[key] instanceof Object && key in target)
        Object.assign(source[key], mergeObjects(target[key], source[key]));
    });
  });
  return Object.assign(target || {}, ...sources);
}

export function getColumnDefinations(
  fields: any,
  customizationParams: any = {},
  extraFields: any = [],
  removeCols: any = [],
) {
 
  const columnDefs = fields?.sort((a: any, b: any) => a.cp - b.cp)?.map((data: any) => { 
    let filterType = 'agMultiColumnFilter'; 

    if (data.dt === 'date') {
      filterType = 'agDateColumnFilter';
    } else if (data.dt === 'number' || data.dt ==='decimal') {
      filterType = 'agNumberColumnFilter';
    }

    const columnDef = {
      colId: data.cc,
      headerName: data.hd,
      field: data.scc,
      initialHide: !data.v,
      pinned: null,
      filter: filterType,
      enablePivot: true,
      initialFlex: 1,
      minWidth: 150,
      valueFormatter: (params: any) => {
        if (params.value) {
          const format = (getNumberFormat() || 'USA').toUpperCase();
          const locale = format === 'USA' ? 'en-US' : format === 'IND' ? 'hi-IN' : undefined;
      
          if (data.dt === 'number') {
            return locale ? params.value.toLocaleString(locale) : params.value;
          }
      
          if (data.dt === 'decimal') {
            const fixedValue = parseFloat(params.value.toFixed(2)); 
            return locale ? fixedValue.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) :fixedValue;
          }
      
          return params.value;
        }
      }, 
      filterParams: {
        buttons: ['reset'], 
        comparator: (filterLocalDateAtMidnight: Date, cellValue: any) => {
          if (!cellValue) return -1;
        
          const cellDate = new Date(cellValue);
          if (isNaN(cellDate.getTime())) return -1;
        
          const cellDateOnly = new Date(
            cellDate.getFullYear(),
            cellDate.getMonth(),
            cellDate.getDate()
          );
        
          if (cellDateOnly < filterLocalDateAtMidnight) return -1;
          if (cellDateOnly > filterLocalDateAtMidnight) return 1;
          return 0;
        }
        
      },
      cellStyle: {
        justifyContent: data.cla
      }
    }; 
    // Apply customization if needed
    if (customizationParams[data.cc]) {
      // Object.assign(columnDef, customizationParams[data.cc]);
      mergeObjects(columnDef, customizationParams[data.cc])
    }
    return columnDef;
  });


  
  // Add extra columns
  extraFields?.forEach((field: any) => {
    let position = field.position;
    // If position is not specified or invalid, add the column at the end
    if (
      position === undefined ||
      position < 0 ||
      position > columnDefs.length
    ) {
      position = columnDefs.length;
    }
    columnDefs?.splice(position, 0, field);
  });

  const finalcolDef = columnDefs?.filter((obj: any) => !removeCols?.includes(obj.colId));
  
  return finalcolDef;
  
}
// ===================================================================================================

// Common methods used in Filter Modal Screen
// ===================================================================================================

// Function to find out the unique values of filter questions
export function findUniqueKeysAndValues(filterData: any) {
  const uniqueValues: any = {};

  // Function to collect keys and values
  function collectKeysAndValues(obj: any) {
    for (const key in obj) {
      if (!uniqueValues[key]) {
        uniqueValues[key] = new Set();
      }
      if (obj[key]) {
        uniqueValues[key].add(obj[key]);
      }
    }
  }

  // Iterate over customers and ordLineItems
  if (filterData.customers) {
    filterData.customers.forEach(collectKeysAndValues);
  }

  if (filterData.ordLineItems) {
    filterData.ordLineItems.forEach(collectKeysAndValues);
  }

  if (filterData.ordAttr) {
    filterData.ordAttr.forEach(collectKeysAndValues);
  }

  // Convert Set to Array and include empty array for missing keys
  const response: any = {};
  for (const key in uniqueValues) {
    response[key] = Array.from(uniqueValues[key]).map((o: any) => ({ label: o, value: o }));
  }

  // Add empty array for any missing keys based on the first object in each array
  const allKeys: any = [
    ...Array.from(new Set([
      ...Object.keys(filterData.customers?.[0] || {}),
      ...Object.keys(filterData.ordLineItems?.[0] || {})
    ]))
  ];

  allKeys.forEach((key: any) => {
    if (!response[key]) {
      response[key] = [];
    }
  });

  return response;
}

// Function to find dynamic attributes of the object that is passed in paramenters
export const getDynamicAttributes = (attributes: any) => {

  if (!attributes || attributes?.length === 0 || Object.keys(attributes).length === 0) {
    return [];
  }
  return attributes?.map((attr: any) => attr.key);
}

export const getKeyName = (attributes: any, key: string) => {
  for (let i = 0; i < attributes.length; i++) {
    if (key === attributes[i].key) {
      return attributes[i].name;
    }
  }
  return ''
}

export const getType = (attributes: any, key: any) => {
    for (let i = 0; i < attributes.length; i++) {
      if (key === attributes[i].key) {
        if(attributes[i].is_number){
          return InputTypes.NumberCompare
        }
        return InputTypes.TextCompare
      }
    }
    return ""
}

// Function to check values already there in Values
  export const formatFilterJSON = (filter: any = {}) => {
  const formatFilter: any = {};

  for (const key in filter) {
    const { filters } = filter[key];
    for (let i = 0; i < filters?.length; i++) {
      const { attributeName, value, type, operator } = filters[i];

      if (value?.length > 0) {
        let formattedVal;

        if (type === 'textCompare') {
          formattedVal = { op: operator ?? 'et', val: value[0].value };
        } else if (type === 'numberCompare') {
          formattedVal = { op: operator ?? 'et', val: parseInt(value[0].value) };
        } else {
          formattedVal = value.map((v: any) => v?.value || v?.id);
        }

        if ((type === 'textCompare' || type === 'numberCompare' )  && !['ide','ov','pbsz','pcbsz'].includes(attributeName)) {
          if (!formatFilter.attributes) formatFilter.attributes = {};
          formatFilter.attributes[attributeName] = formattedVal;
        } else {
          formatFilter[attributeName] = formattedVal;
        }}
      }
    }

  // Cleanup empty or invalid entries
  Object.keys(formatFilter).forEach(key => {
    if (formatFilter[key]?.val === '') {
      delete formatFilter[key];
    }
  });

  Object.keys(formatFilter).forEach(key => {
    if (
      (formatFilter[key]?.op && (formatFilter[key]?.val === undefined || formatFilter[key]?.val === null)) ||
      (formatFilter[key]?.val && (formatFilter[key]?.op === undefined || formatFilter[key]?.op === null))
    ) {
      delete formatFilter[key];
    }
  });

  return formatFilter;
};



export const checkValue = (filters: any, value: any) => {
  for (let i = 0; i < filters.length; i++) {
    if (filters[i]?.id === value || filters[i]?.value === value) {
      return true;
    }
  }
  return false;
}

export const getSelectedFilters = (filter: any, isMfgStrgyIncluded: any) => {
  const selectedFilter: any = {};
  for (const key in filter) {
    const { filters, label } = filter[key];
    const newFilter: any = {
      name: label,
      parentId: key,
      filters: []
    }

    for (let i = 0; i < filters?.length; i++) {
      const { name, attributeName, value, type, operator } = filters[i];

      if (attributeName === 'ms') {
        if (value?.length > 0 && isMfgStrgyIncluded) {
          newFilter.filters.push({ filterId: attributeName, type, operator, label: name, value: value?.filter((v: any) => v.value || v.id) });
        }
      } else {
        if (Array.isArray(value) && value.length > 0) {
          newFilter.filters.push({ filterId: attributeName, type, operator, label: name, value: (value[0]?.value===0)?  
            [{value: '0', label: '0'}]: value?.filter((v: any) => v.value || v.id) });
        }
      }
    }

    if (newFilter?.filters?.length > 0) {
      selectedFilter[key] = { ...newFilter };
    }



  }

  return selectedFilter;
}

export const getBodyForExcelExport = ({
  headersdata,
  filterData = {},
  colDefMap,
  groupedColDefsRef,
}: any) => {
  const filteredHeadersData = headersdata?.filter(
    (col: any) =>
      col.colId !== "DropDown" && col.colId !== "Action" && col.hide !== true && !col.colId.includes('History') && (col.colId!=="Default Attribute-Remark")

  );

  try {
    // Grouped data
    if (groupedColDefsRef?.current) {

      const groupedColumnData: any = [];
    
      filteredHeadersData.forEach((headerItem: any) => {
        groupedColDefsRef?.current.forEach((groupDef: any) => {
          const header = groupDef.ch.find((subHeader: any) => subHeader.groupHeaderKey === headerItem.colId);
    
          if (!header) return;

          const last = groupedColumnData[groupedColumnData.length - 1];

          if (last && last.cc === groupDef.cc) {
            last.ch.push(header);
          } else {
            groupedColumnData.push({ cc: groupDef.cc, ch: [header] });
          }

        });
      });

      return {
        headers: groupedColumnData,
        isGrouped: true,
        ...filterData,
      };
      
    }
    // Flat data
    else {
      const headers = filteredHeadersData
        ?.map((col: any) => {
          const header_data = colDefMap?.current?.get(col.colId);
          return {
            ...header_data,
          };
        })
        .filter(
          (col: any) => col?.hd !== undefined && col?.scc !== undefined
        );

      return {
        headers,
        ...filterData,
      };
    }
  } catch (e) {
    console.log(e);
  }
};

export const DownloadExcel = (response : any,filename = "ReportFile") => {
  try {
    if ((response.headers['content-type'] === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') || (response.headers['content-type'] ===  'application/octet-stream')) {
      const blob = new Blob([response.data], { type: response.headers['content-type'] });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${filename}__${format(Date.now(), "dd/MM/yyyy")}.xlsx`); // Use extracted filename
      document.body.appendChild(link);
      link.click();
      URL.revokeObjectURL(url);
      document.body.removeChild(link);
      return true;
    } else {
      notifyError('No orders found to export data!');
      return false;
    }
  } catch (e) {
    console.log(e);
  }
};


export const DownloadExcelMTA = (response: any, filename = "ReportFile") => {
  try {
    const responseData = response.data?.data || response;
    const binaryString = atob(responseData.fileContent);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const blob = new Blob([bytes.buffer], { type: responseData.fileType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${filename}__${format(Date.now(), "dd/MM/yyyy")}.xlsx`);
    document.body.appendChild(link);
    link.click();
    URL.revokeObjectURL(url);
    document.body.removeChild(link);
  } catch (e) {
    console.error("Error downloading Excel file:", e);
    notifyError("Something went wrong");
  }
};

export const CsvExportMTA = async ( payload: any, filename = "ReportFile") => {
  try {
    const response = await axios.post(
      process.env.REACT_APP_API_HOST + `api/mta/GetExportDataAsync`,
      payload,
      {
        withCredentials: true, 
        responseType: 'blob',  
        headers: {
            "Content-Type": "application/json" 
        }
      }
    );
 
    const blob = await response.data;
    const contentType = response.headers['content-type']; 
    const fileExtension = getFileExtensionFromContentType(contentType);
    const downloadFileName = `${filename}__${format(Date.now(), "dd-MM-yyyy")}.${fileExtension}`;
 
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.setAttribute("download", downloadFileName);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(blobUrl);
  } catch (e) {
    console.error("Error downloading file:", e);
    notifyError("Something went wrong while exporting");
    throw e;
  }
};
 
// Optional helper
const getFileExtensionFromContentType = (contentType: string | null) => {
  switch (contentType) {
    case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
      return "xlsx";
    case "text/csv":
      return "csv";
    default:
      return "bin";
  }
};

// MDM MTO Utils
export const mapDraftToMTOColumnDefs = (fields: Field[], customParams?: ColDef) => {
  let result: ColDef[] = []
  result = fields.map((f) => {
    return {
      field: f.key,
      colId: f.key,
      headerName: f.displayName,
      minWidth: 180,

      cellStyle: {
        "textAlign": "center",
      },
      flex: 1,
      cellRenderer: f.key === "action" && MTOActionRenderer,
      filter: f.key !== "action" && "agMultiColumnFilter",
      ...customParams
    }
  })
  return result
}


export const mapDraftDataToMTOTableRowData = (rowData: any[]) => {
  let result = []
  if (!rowData) return
  result = rowData.map((row) => {
    return {
      ...row,
      LastModifiedDateTime: row.LastModifiedDateTime
    }
  })

  result.sort((a, b): any => {
    return differenceInSeconds(b.LastModifiedDateTime, a.LastModifiedDateTime)
  })

  result = result.map((r: any, index: number) => {
    return { ...r, sr_no: index + 1, LastModifiedDateTime: r.LastModifiedDateTime }
  })
  return result
}

export const parseMTOExcelData = async (file: File, master: MDMMasterState, pageType: string) => {
  const currMasterKeys = master.fields?.map((field) => field.key) || [];
  const buffer = await file.arrayBuffer();
  const numberOfSheets = await readSheetNames(file);

  // Validate sheet constraints
  if (numberOfSheets.length > 1) {
    throw new Error('File cannot contain multiple sheets');
  }

  // Parse Excel data
  const data = await readXlsxFile(buffer, { parseNumber: (string) => string });

  // Validate row count
  const recordLimit = parseInt(process.env.REACT_APP_RECORD_UPLOAD_LIMIT_MTO || "50000", 10);
  if (data.length > recordLimit) {
    throw new Error(`Number of rows should not exceed ${recordLimit}`);
  }

  // Check for duplicate headers
  const headersRow = data[0];
  const isDuplicateHeader = new Set(headersRow).size !== headersRow.length;
  if (isDuplicateHeader) {
    throw new Error("File Contains Duplicate Headers");
  }

  // Map headers to master field keys
  const headerKeys = headersRow.map((headerName:any) => {
    const field = master.fields?.find((field) => field.displayName === headerName);
    return field ? field.key : headerName;
  });

  // Check for missing headers and invalid headers while adding through excel
  const missingHeaders = currMasterKeys.filter((key) => !headerKeys.includes(key));
  if (pageType === 'add' && missingHeaders.length > 0) {
    throw new Error(`File is missing the following columns: ${missingHeaders.map((key) => {
      return master.fields?.find((field) => field.key === key)?.displayName;
    }).join(', ')}`);
  }

  const invalidHeaders = headerKeys.filter((key:any) => !currMasterKeys.includes(key));
  if (invalidHeaders.length > 0) {
    throw new Error(`File contains columns ${invalidHeaders.join(', ')}, which are not valid columns`);
  }

  // Validate data presence
  if (data.slice(1).length === 0) {
    throw new Error('File Contains zero rows.');
  }

    if (master.id === 501 || master.id === 502 || master.id === 503 || master.id === 504) {

    const bufferData: any = [];
    for (let i = 1; i < data?.length; i++) {
      const buffData: any = {};
      for (let j = 0; j < data[i].length; j++) {
        buffData[headerKeys[j]] = data[i][j];
      }
      buffData["err"] = "";
      bufferData.push(buffData);
    }
    return bufferData;
  }

  return [];
};

export const generateMTOFilterOptions = (data: Master[], currentFilters:any) => {
  const temp: string[] = [];
  const options: Option[] = [];
  if (!data) return options
  data.forEach((master: Master) => {
    const tempMasterFields = [...master.fields]
    const tempFields = tempMasterFields.sort((a: Field, b: Field) => parseInt(a.col_Position) - parseInt(b.col_Position))
    tempFields.forEach((field: Field) => {
      if (!temp.includes(field.displayName) && field.visible) {
        temp.push(field.displayName);
        options.push({ value: field.key, label: field.displayName, })
      }
    })
  });
  const finOptions: any[] = options.filter((ele: any) => {
    return !currentFilters.some((e: any) => e.field === ele.value);
  });
  // console.log('fin options', finOptions);
  return finOptions;

}
export const getMDMTableHeight = (activeMaster:MDMMasterState):string=>{
  // return activeMaster.progress==='view' ? "calc(100% - 70px)" : "95%" 

  if(activeMaster.progress === 'default' && activeMaster.id == 10){
    return "calc(100% - 70px)"
  }

  if(activeMaster.progress === 'view'){
    
   

    return "calc(100% - 70px)"
  }

  return 'calc(95% - 10px)'

}


export const downloadBase64Image = (base64Data: any, fileName: string):any => {
  const downloadLink = document.createElement('a');
  downloadLink.href = base64Data;
  downloadLink.download = fileName;
  document.body.appendChild(downloadLink);
  downloadLink.click();
  document.body.removeChild(downloadLink);
}

// ===================================================================================================

export function getColumnDefinationsMTA(
  fields: any,
  customizationParams: any = {},
  extraFields: any = [],
  removeCols: any = [],
) {
  const columnDefs = fields?.map((data: any) => {
    const columnDef = {
      colId: data.Col_Code || data.colCode,
      headerName: data.Header || data.header,
      field: data.Col_Code || data.colCode,
      initialHide: !data.Visible,
      initialPinned: null,
      initialSort: null,
      sortIndex: null,
      aggFunc: null,
      rowGroup: false,
      rowGroupIndex: null,
      initialPivot: false,
      enablePivot: true,
      enableRowGroup:false,
      enableValue:true,
      pivotIndex: null,

      flex: 1,
      minWidth: 180,
      cellStyle: {
        justifyContent: data.CellAlignment
      },
      cellRenderer: CellRenderersMapping[data.Col_Code || data.colCode],
      cellDataType: getCellDataType(data.DataType),
      filter: getCellFilter(data.DataType),
      filterParams: filterParams,
      position: data.Col_Position,

      ...(getCellDataType(data.DataType) === 'number' && {
        valueFormatter: (params: any) => {
          const format = (process.env.REACT_APP_NUMBER_FORMAT || '').toUpperCase();
          const locale = format === 'USA' ? 'en-US' : format === 'IND' ? 'hi-IN' : undefined;
          if(params.value == null || isNaN(params.value)) return ''
          else if(locale)  return params.value.toLocaleString(locale);
          return params.value;
          // return params.value == null || isNaN(params.value) ? '' : params.value;
        }
      })
    };
    // Apply customization if needed
    if (customizationParams[data.Col_Code || data.colCode]) {
      // Object.assign(columnDef, customizationParams[data.Col_Code]);
      mergeObjects(columnDef, customizationParams[data.Col_Code || data.colCode])
    }
    return columnDef;
  });
  
  // Add extra columns
  // If position is not specified or invalid, add the column at the end
  extraFields?.forEach((field: any) => {
    const position = field.position;
    if (
      position === undefined ||
      position < 0 ||
      position > columnDefs.length
    ) {
      field.position = columnDefs.length;
    }
  });
  
  //add extraFields in columnDefs
  columnDefs.push(...extraFields);

  //sort all column accordinglly position 
  columnDefs.sort((a: any, b: any) => a.position - b.position);

  //remove columns matching "removeCols"
  const finalcolDef = columnDefs
    ?.filter((obj: any) => !removeCols?.includes(obj.colId))
    .map((columnDef: any) => {
      const sanitizedColumnDef = { ...columnDef };
      delete sanitizedColumnDef.position;
      return sanitizedColumnDef;
    });

  return finalcolDef;

}

export function getCCRNamesFromId(ccrsData:any,ccrIds:number[]){
  if(!Array.isArray(ccrsData) || !ccrsData || !ccrIds||  !ccrsData?.length || !ccrIds.length){
    return ""
  }

  const ccrNameFromId = ccrIds.map((id:number)=> ccrsData.find((ccr:any)=> ccr.cid == id)?.cnm).join(', ')
  return ccrNameFromId ? ccrNameFromId : "";
}

export const getNestedChildren = (children: Array<any>): any => {
  const stack = children? [...children]:[];
  const result = [];
  while (stack.length > 0) {
    const current = stack.pop();
    if (current.child) {
      stack.push(...current.child);
    } else {
      result.push(current);
    }
  }
  return result.reverse();
};
