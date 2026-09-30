import { ProcurementLayout } from '../styles';
import ActionToolBar from "../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import useSimFullKit from '../SimulateFullKit/useSimFullKit';
import VFFloatingTab from "../../../../../../components/VectorFLOW/commons/VFFloatingTab";
import { useUserData } from "../../../../../../context";
import { useNavigate } from 'react-router';


const SimulateFullKit = () => {
    const { renderView, toggleCurrentTab, handleResetClick, handleSaveClick, ExcelExportData} = useSimFullKit();
    const { user } = useUserData();
    const navigate = useNavigate();
    const themeUi = user.user.theme_ui;
    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100%", paddingBottom: "2rem" }}>

            <ActionToolBar
                // excel export api is not available for now , once api ready uncomment bellow line
                // isExcelExport 
                onExcelExportClick={ExcelExportData}
                isGoBackButton
                handleGoBack={() => {
                    navigate('/mto/procurement-planning/planning')
                }}
                themeUi={themeUi}
                comp={'Procurement Planning'}
                onDateChange={() => { console.log('') }}
                submitDate={() => { console.log('') }}
                handleSaveClick={handleSaveClick}
                handleResetClick={handleResetClick}
            />
            <div style={{ zoom: 0.75, display: 'flex', justifyContent: 'center', marginBottom: '2px' }}>

                <VFFloatingTab
                    handleClick={(tab) => toggleCurrentTab(tab)}
                    tabs={[
                        {
                            id: 'iof',
                            label: 'Incremental Order In Full Kit',
                            value: 'iof'
                        },
                        {
                            id: 'cf',
                            label: 'Cumulative Full Kit',
                            value: 'cf'
                        }
                    ]}
                />

            </div>
            <ProcurementLayout>
                {renderView()}
            </ProcurementLayout>
            {/* <text onClick={Save} style={{ fontSize: 34 }}>save</text> */}
        </div>
    )
}

export default SimulateFullKit