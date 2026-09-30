import { forwardRef} from "react";
import { AgGridReact, AgGridReactProps } from "ag-grid-react";
import { VFTableWrapper } from "./styles";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import './styles.css'
import { useUserData } from "../../../../context";


interface VFTableProps extends AgGridReactProps {
  height?:string,
  disableZoomScaling?:boolean
}


const VFTable = forwardRef((props: VFTableProps, ref: any) => {

  const  {user} = useUserData()

  const theme = user.user.theme_ui

  const getClassName= ()=>{
    switch(theme){
      case "NOIRFUSION":
        return "ag-theme-noir-fusion"
      case "REGALBLAZE":
        return "ag-theme-regal-blaze"
      case "PUREELEGANCE":
        return "ag-theme-pure-elegance"
      case "CHARCOALCHIC":
        return "ag-theme-charcoal-chic"
      default:
        return "ag-theme-noir-fusion"
    }
  }
  
  return (
    <VFTableWrapper className={`${getClassName()} ag-theme-alpine`} role={"table"} height={props.height} disableZoomScaling={true}>
      <AgGridReact
        ref={ref}
        {...props}
        rowHeight={30}
        defaultColDef={{
          resizable:true,
          ...props.defaultColDef
        }}
        paginationPageSizeSelector={false}
        suppressDragLeaveHidesColumns={true}
      />
    </VFTableWrapper>
  );
});

export default VFTable;