import { useMemo } from 'react';
import VFTable from '../Common/VFTable';
import { mapProcPlanningChildrenFieldsToColDefs } from '../../../../helpers/utils';
import GetProcHeaderChildren from './Planning/GetProcHeaderChildren.json';
import ChildrenColor from "../Common/ChildrenColor/ChildrenColor";
import { ChildTableWrapper } from './Planning/styles';

const ChildrenProcPlanningCellRenderer = (params: any) => {
    const {colDef} = params

    const customChildrenCellRenderers = useMemo(() => ({
        "coloPriorityOfBall": ChildrenColor
    }), []);

    return (
        <div>
            <ChildTableWrapper>

                <VFTable
                    data-testid='VFTable'
                    disableZoomScaling
                    className='child-grid'
                    columnDefs={colDef}
                    defaultColDef={{
                        cellStyle: {
                            'text-align': 'center',
                            'height': '50px',
                            "font-style": "normal",
                            "font-variant": "normal",
                            "font-weight": "300",
                            "font-size": "20px",
                            "font-family": "Roboto",
                            'text-overflow': 'ellipsis',
                            'white-space': 'nowrap',
                            'resizable': 'true',
                            'background': 'white',
                        },
                        flex: 1,
                    }}
                    rowData={params.data && params.data.children ? params.data.children : []}
                    height={'180px'}
                    pagination={true}
                    components={customChildrenCellRenderers}
                    masterDetail={true}
                    rowSelection="multiple"
                    suppressRowClickSelection={true}
                    enableRangeSelection={true}
                    paginationPageSize={3}
                    
                    hideStatusBar={true} 
                    sideBar={false} 
                />
            </ChildTableWrapper>
        </div>
    );
};

export default ChildrenProcPlanningCellRenderer;
