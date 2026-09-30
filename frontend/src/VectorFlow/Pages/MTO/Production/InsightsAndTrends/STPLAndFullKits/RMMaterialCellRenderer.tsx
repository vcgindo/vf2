import { GridOptions } from 'ag-grid-enterprise'
import { useMemo } from 'react';
import { getColumnDefinations } from '../../../../../../helpers/utils';
import VFTable from '../../../Common/VFTable';
import { rmMaterialConfigCol } from './ColumnData';

const CustomHeader = ({ headerName }: any) => {
  return (
    <div
      style={{
        fontFamily: "Roboto",
        background: "black",
        fontWeight: "500",
        fontSize: "14px",
        color: "#FFFFFF",
        display: "flex",
        alignItems: "center",
        textAlign: "center",
        justifyContent: "center",
        borderRadius: "10px",
        padding: "0px 20px"
      }}
    >
      {headerName}
    </div>
  );
};


const RMMaterialCellRenderer = (params: any) => {

  const colDefCustomizations = {
    rm_material: {
      headerComponent: () => <CustomHeader headerName="RM Material" />,
    }
  }

  const colDefs = useMemo(() => {
    return getColumnDefinations(rmMaterialConfigCol, colDefCustomizations, [])
  }, []);

  const options: GridOptions<any> = {
    columnDefs: colDefs,
    defaultColDef: {
      suppressMenu: true,
      cellStyle: {
        textAlign: "center"
      },
      resizable: true
    },
  }


  return (
    <div style={{ padding: "2rem" }}>
      <VFTable
        className='child-grid'
        pagination={true}
        gridOptions={options}
        rowData={params.data?.children}
        height={"300px"}
        disableZoomScaling={true}
        onGridReady={(params: any) => {
          params.api?.autoSizeAllColumns()
        }}
      />
    </div>
  )
}

export default RMMaterialCellRenderer;