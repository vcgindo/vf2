import {useState,useEffect,useCallback, useRef} from 'react'
import VFTable from "../../VectorFLOW/commons/VFTable"
import { TableWrapper } from "../UserURLsDrawer/styles"
import {  Skeleton } from "../../commons/styled"
import { notifyError } from '../../../helpers/notify'
import { useGetAdminPermissions } from '../../../VectorFlow/Services/MTA/MDM'
import { useSelector } from 'react-redux'
import { RootState } from '../../../redux/store/store'
import ErrorCell from './ErrorCell';
import { GridRef } from '../../../VectorFlow/types/MDM'
import { GridFilterWrapper, TextBtn } from '../../../VectorFlow/Pages/MTO/Common/VFPagination/styles'
import { useUserData } from '../../../context'

export const getProductColumns = (envConfig: any) => [
    { colId: "id", field: "id", headerName: "ID" },
    { colId: "productHierarchy1", field: "product_hierarchy_1", headerName: envConfig['PRODUCT_PERMISSION_L1'] },
    { colId: "productHierarchy2", field: "product_hierarchy_2", headerName: envConfig['PRODUCT_PERMISSION_L2'] },
    { colId: "productHierarchy3", field: "product_hierarchy_3", headerName: envConfig['PRODUCT_PERMISSION_L3'] },
];

export const getLocationColumns = (envConfig: any) => [
    { colId: "id", field: "id", headerName: "ID" },
    { colId: "locationHierarchy1", field: "location_heirarchy_1", headerName: envConfig['LOCATION_PERMISSION_L1'] },
    { colId: "locationHierarchy2", field: "location_heirarchy_2", headerName: envConfig['LOCATION_PERMISSION_L2'] },
    { colId: "locationHierarchy3", field: "location_heirarchy_3", headerName: envConfig['LOCATION_PERMISSION_L3'] },
];

export const getErrorProductColumns = (envConfig: any) => [
    { colId: "errors", field: "errors", headerName: "Errors" ,cellRenderer:ErrorCell ,  suppressColumnsToolPanel:true,wrapText:true, autoHeight:true},
    { colId: envConfig['PRODUCT_PERMISSION_L1'], field: envConfig['PRODUCT_PERMISSION_L1'], headerName: envConfig['PRODUCT_PERMISSION_L1'] },
    { colId: envConfig['PRODUCT_PERMISSION_L2'], field: envConfig['PRODUCT_PERMISSION_L2'], headerName: envConfig['PRODUCT_PERMISSION_L2'] },
    { colId: envConfig['PRODUCT_PERMISSION_L3'], field: envConfig['PRODUCT_PERMISSION_L3'], headerName: envConfig['PRODUCT_PERMISSION_L3'] },
];

export const getErrorLocationColumns = (envConfig: any) => [
    { colId: "errors", field: "errors", headerName: "Errors" ,cellRenderer:ErrorCell ,  suppressColumnsToolPanel:true,wrapText:true, autoHeight:true},
    { colId: envConfig['LOCATION_PERMISSION_L1'], field: envConfig['LOCATION_PERMISSION_L1'], headerName: envConfig['LOCATION_PERMISSION_L1'] },
    { colId: envConfig['LOCATION_PERMISSION_L2'], field: envConfig['LOCATION_PERMISSION_L2'], headerName: envConfig['LOCATION_PERMISSION_L2'] },
    { colId: envConfig['LOCATION_PERMISSION_L3'], field: envConfig['LOCATION_PERMISSION_L3'], headerName: envConfig['LOCATION_PERMISSION_L3'] },
];
const ViewPermissions = (props:{permissionType: string})=>{
    const {  permissionType } = props
    const [rowData,setRowData] = useState<Array<any>>([])
    const [isLoading,setIsLoading] = useState<boolean>(true)
    const [hasData, setHasData] = useState<boolean>(true);


    const { mutateAsync: getPermissions } = useGetAdminPermissions();
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);

    const getPermissionsData = useCallback(async(type: string)=>{
        setIsLoading(true);
        try{

            const result = await getPermissions();

            let data;
            if (type === 'Product_Permissions') {
                data = result?.data?.product;
            } else if (type === 'Location_Permissions') {
                data = result?.data?.location;
            }
            setRowData(data || []);
            setHasData(data && data.length > 0);
        }catch(error:any){
            console.error(error);
            notifyError("Server Went Unresponsive");
            setRowData([]);
            setHasData(false);
        }finally{
            setIsLoading(false);
        }
    },[getPermissions])

    useEffect(()=>{

        getPermissionsData(permissionType);
    },[permissionType, getPermissionsData])

    const productColumns = getProductColumns(EnvConfig);
    const locationColumns = getLocationColumns(EnvConfig);
    const columnDefs = permissionType === 'Product_Permissions' ? productColumns : locationColumns;
    const ref = useRef<GridRef>();
    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    const {user} = useUserData()
    const themeUi = user.user.theme_ui
    const clearGridFilter = () =>{   
        ref?.current?.api.setFilterModel(null);
          setIsDisabled(true);
    }

    const CustomStatusPanel = () => {
        return (
            <GridFilterWrapper style={{marginTop:'25px'}}>
                <TextBtn onClick={clearGridFilter} disabled={isDisabled} themeUi={themeUi}>
                    Clear All Grid Filters
                </TextBtn>  
            </GridFilterWrapper>           
        );
    };

    if(isLoading){
        return (
            <Skeleton style={{height:400,width:'100%'}}/>
        )
    }

    if (!hasData) {
        return (
            <div style={{height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                <p>No {permissionType === 'Product_Permissions' ? 'Product' : 'Location'} Permissions Found</p>
            </div>
        )
    }

    return(
        <TableWrapper>
            <VFTable 
                ref={ref}
                defaultColDef={{
                    flex:1,
                    cellStyle:{ 'text-align':'center' },
                    floatingFilter: true,
                    filter: "agMultiColumnFilter"
                }}
                rowHeight={50}
                height="600px"
                rowData={rowData}
                columnDefs={columnDefs}
                onFilterChanged={() => {
                    const filterModel = ref?.current?.api?.getFilterModel();
                    if (filterModel && Object.keys(filterModel).length > 0) {
                      setIsDisabled(false);
                    } else {
                      setIsDisabled(true);
                    }
                  }}

                  statusBar={{
                    statusPanels: !isLoading?[
                      { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                      { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                      { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                      { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                      { statusPanel: 'agAggregationComponent', align: 'left' },
                      { statusPanel: CustomStatusPanel, align: "right" },

                    ]:
                    [],
                  }}
            />
        </TableWrapper>
    )
}

export default ViewPermissions
