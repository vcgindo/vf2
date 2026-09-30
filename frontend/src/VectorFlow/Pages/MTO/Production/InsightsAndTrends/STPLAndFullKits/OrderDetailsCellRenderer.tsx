import { GridOptions } from 'ag-grid-enterprise'
import { useMemo } from 'react';
import { getColumnDefinations } from '../../../../../../helpers/utils';
import VFTable from '../../../../../../components/VectorFLOW/commons/VFTable'
import { orderDetailsConfigCol } from './ColumnData';
import RMMaterialCellRenderer from './RMMaterialCellRenderer';

const BarFillUI = (value: any) => {
  const val = value?.value || 0;
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '5px' }}>
      <div>{val || 0}</div>
      <div style={{ display: 'flex', minWidth: '100px', background: 'lightgray' }}>
        <div style={{
          height: '20px', backgroundImage: 'linear-gradient(to right, #8d2e61, #bb3f81, #db6ba7)',
          borderRadius: '2px', width: `${val}px`
        }} />
      </div>
    </div>
  );
};

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


const OrderDetailsCellRenderer = (params: any) => {

  const colDefCustomizations = {
    fk: {
      cellRenderer: (params: any) => <BarFillUI value={params?.value} />,
    },
    order_details: {
      headerComponent: () => <CustomHeader headerName="Order Details" />,
    },
    or_id: {
      cellRenderer: "agGroupCellRenderer",
    }
  }

  const colDefs = useMemo(() => {
    return getColumnDefinations(orderDetailsConfigCol, colDefCustomizations, [])
  }, []);

  const options: GridOptions<any> = {
    columnDefs: colDefs,
    masterDetail: true,
    defaultColDef: {
      suppressMenu: true,
      cellStyle: {
        textAlign: "center"
      },
      resizable: true
    },
    detailCellRendererParams: {
      innerHeight: 400,
    },
    detailCellRenderer: RMMaterialCellRenderer,
  }


  return (
    <div style={{ padding: "2rem" }}>
      <VFTable
        className='child-grid'
        pagination={true}
        gridOptions={options}
        rowData={params.data?.children}
        height={"400px"}
        disableZoomScaling={true}
        onGridReady={(params: any) => {
          params.api?.autoSizeAllColumns()
        }}
      />
    </div>
  )
}

export default OrderDetailsCellRenderer;