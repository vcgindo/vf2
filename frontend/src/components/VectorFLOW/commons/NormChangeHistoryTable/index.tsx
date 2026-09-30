import VFModalCard from "../VFModalCard"
import { ColDef } from 'ag-grid-enterprise'; 
import { AgGridReact } from "ag-grid-react";
import { useUserData } from "../../../../context";
import {ButtonWrapper, AgGridWrapper, AgContainer} from './styles'
import './styles.css'
import { useDispatch } from 'react-redux';
import { TOGGLE_NORM_CHANGE_HISTORY_TABLE } from "../../../../redux/actions/MTA";
import VFButton from "../VFButton";
interface NormChangeHistoryTableProps {
    data:any
    onGoBack?:()=>void
}

const NormChangeHistoryTable = (props : NormChangeHistoryTableProps)=> {

    const {user} = useUserData()
    const themeUi=user?.user?.theme_ui;
    const dispatch = useDispatch();

    const {
        data
    } = props

    const CustomHeader = ({headerName}: any) => {
        return <div style={{ fontSize: "16px", display: "flex", alignItems: "center", textAlign:'center', justifyContent:'center' }}>{headerName}</div>; 
      };

      
    // const rowData = [
    //     { col1: '21 June', col2: '2', col3: '3', col4:'stockout has occured today.stockout done today and ready for the next stock to be delieverd,'},
    //     { col1: '22 June', col2: '3', col3: '4',col4:'stockout has occured today'},
    //   ];
    const columnDefs: ColDef[] = [
      {
        headerName: "Change Date",
        field: "nCD",
        colId: "nCD",
        minWidth: 150,
        flex: 1,
        cellStyle: {
          fontSize: "14px",
          alignItems: "center",
          display: "flex",
          justifyContent: "center",
        },
        headerComponent: () => <CustomHeader headerName="Change Date" />,
      },
      {
        headerName: "Old Norm",
        field: "olN",
        colId: "olN",
        minWidth: 110,
        flex: 1,
        cellStyle: {
          fontSize: "14px",
          alignItems: "center",
          display: "flex",
          justifyContent: "center",
        },
        headerComponent: () => <CustomHeader headerName="Old Norm" />,
      },
      {
        headerName: "New Norm",
        field: "nN",
        colId: "nN",
        minWidth: 110,
        flex: 1,
        cellStyle: {
          fontSize: "14px",
          alignItems: "center",
          display: "flex",
          justifyContent: "center",
        },
        headerComponent: () => <CustomHeader headerName="New Norm" />,
      },
      {
        headerName: "Reason",
        field: "rsn",
        colId: "rsn",
        minWidth: 290,
        flex: 2,
        cellRenderer: "wrapTextCellRenderer",
        autoHeight: true,
        resizable: true,
        sortable: true,
        wrapText: true,
        cellStyle: {
          wordBreak: "normal",
          fontSize: "14px",
          lineHeight: "20px",
          alignItems: "center",
          display: "flex",
          textAlign: "left",
        },
        headerComponent: () => <CustomHeader headerName="Reason" />,
      },
    ];

    return(
        <>
        <VFModalCard openModal={true}  headerText={'Norm Change History'} headerIcon={'/assets/img/VectorFLOW/BPR/historynorm.svg'} closeIcon={''} paddingLeftAndRight={0}  headerTextColor={'black'} backgroundColor={'f4f4f4'} data-testid="vfmultifilter-img" >
            <AgContainer>
                <AgGridWrapper>
                    <div className="ag-theme-alpine "  style={{ height: '200px', width:'700px',textAlign:'center' }}>  
                        <AgGridReact
                        rowData={data===null ? [] : data}
                        columnDefs={columnDefs}
                    />
                     </div>
                 </AgGridWrapper> 
            </AgContainer>
            <ButtonWrapper>
                <VFButton themeUi={themeUi} onClick={()=>dispatch(TOGGLE_NORM_CHANGE_HISTORY_TABLE(false))} width={160} style={{display:'flex', alignItems:'center', height:'40px', textAlign:'center',justifyContent: 'center'}}>Go Back!</VFButton>
            </ButtonWrapper>
        </VFModalCard>
        </>
    )
}

export default NormChangeHistoryTable