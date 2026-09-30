

import { forwardRef} from "react";
import { AgGridReact, AgGridReactProps } from "ag-grid-react";
import { VFTableWrapper } from "../../../../../components/VectorFLOW/commons/VFTable/styles";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import './styles.css'
import {useUserData} from '../../../../../context'

interface VFTableProps extends AgGridReactProps {
  height?:string,
  disableZoomScaling?:boolean
}


const CustomVFTable = forwardRef((props: VFTableProps, ref: any) => {
  const  {user} = useUserData()

  const theme = user.user.theme_ui

  const getClassName= ()=>{
    switch(theme){
      case "NOIRFUSION":
        return "ag-theme-btr-noir-fusion"
      case "REGALBLAZE":
        return "ag-theme-btr-regal-blaze"
      case "PUREELEGANCE":
        return "ag-theme-btr-pure-elegance"
      case "CHARCOALCHIC":
        return "ag-theme-btr-charcoal-chic"
      default:
        return "ag-theme-btr-noir-fusion"
    }
  }

  return (
    <VFTableWrapper style={{margin:'0px 0px 0px 0px'}} className={`${getClassName()} ag-theme-alpine`} role={"table"} height={props.height}  disableZoomScaling={props.disableZoomScaling}>
      <AgGridReact
        ref={ref}
        {...props}
      />
    </VFTableWrapper>
  );
});

export default CustomVFTable;
