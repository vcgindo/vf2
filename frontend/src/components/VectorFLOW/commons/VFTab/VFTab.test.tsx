import { render, fireEvent, screen} from '@testing-library/react';
import VFTab from './index';
import { type MDMMasterState, type MDMStore}  from "../../../../VectorFlow/types/MDM";
import _ from 'lodash';
import { Provider } from 'react-redux';
import { ReactNode } from 'react';
import { createStore } from '../../../../redux/store/store';
import {QueryClientProvider} from '@tanstack/react-query';
import { setupReactQuery } from '../../../../config/react-query-config';
import { BrowserRouter as Router } from 'react-router-dom'
import { UserDataContext } from '../../../../context';
import { MasterData } from '../../../../mock-data/MDM';
import { mapMasterToColumnDefs } from '../../../../helpers/utils';



const queryClient = setupReactQuery()

const contextWrapper = (children:ReactNode,store:any) => {
  return(
    <QueryClientProvider client={queryClient}>
        <Router>
          <Provider store={store}>
            <UserDataContext.Provider value={{user:{user:{theme_ui:'NOIRFUSION'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}>
                {children}
            </UserDataContext.Provider>
          </Provider>
        </Router>
      </QueryClientProvider>
  )
}







describe('View Modify Component', () => {

  const mockState:MDMStore = {
    allMasters:MasterData,
    masters:MasterData,
    options:[],
    selectedOptions:[],
    activeMaster:{id:1,fields:MasterData[0].fields,filters:MasterData[0].filters,progress:'default',name:MasterData[0].name,colDefs:mapMasterToColumnDefs(MasterData[0].fields),rowData:[], isChecked:true},
    isSelectMasterOpen:true,
    draftId:'',
    isUploadModalOpen:false,
    chunkSize:100,
    recordCount:0,
    isDataAvailableLocally:true,
    lastRunDate:''
  }

  const themeUi = 'NOIRFUSION';
  const handleTabClose = jest.fn();
  const handleTabChange = jest.fn();
  const newTabHandler = jest.fn();

  const props = {
    activeMaster:mockState.activeMaster,
    themeUi:themeUi,
    onTabChange:handleTabChange,
    onTabClose:handleTabClose,
    newTabTitle:'Add Master',
    newTabIcon:"/assets/img/VectorFLOW/NMS/add-circle.svg",
    newTabHandler:newTabHandler
  
  }

  const mockStore = createStore(mockState);

  


  it('renders the VF Tab component', () => {

    render(contextWrapper(<VFTab {...props}/>,mockStore))
  
  });

  it('changes tab when clicking', () => {

    render(contextWrapper(<VFTab {...props}/>,mockStore))

    const tabsList = screen.getAllByTestId('tab-button');
    const tabNo = _.random(1,tabsList.length-1);  
    fireEvent.click(tabsList[tabNo]);

  });

  it('closes tab when clicking close icon', () => {

    render(contextWrapper(<VFTab {...props}/>,mockStore))

    const tabCloseBtn = screen.getAllByTestId('tab-close')[0];
    fireEvent.click(tabCloseBtn)
    expect(handleTabClose).toHaveBeenCalled();

  });

  it('calls New Tab Handler on clickng add new tab', () => {

    render(contextWrapper(<VFTab {...props}/>,mockStore))

    const addNewTab = screen.getByTestId('new-tab');
    fireEvent.click(addNewTab);
    expect(newTabHandler).toHaveBeenCalled();

  });

  it('Renders component correctly when new tab details are not provided (i.e. optional props)', () => {

    render(contextWrapper(<VFTab {...props} newTabHandler={undefined}/>,mockStore));

  });

  it('Renders component correctly when current tab is not in the list of all masters', () => {

    render(contextWrapper(<VFTab {...props} />,mockStore));
    const tabCloseBtn = screen.getAllByTestId('tab-close')[0];
    fireEvent.click(tabCloseBtn)
    expect(handleTabClose).toHaveBeenCalled();

  });

  it('Displays Completed UI when Master is submitted', () => {

    const updatedMasterData:MDMMasterState[] = MasterData.map((master:MDMMasterState)=>{
      if(master.id === 1) return {...master,progress:'submitted'}
      return master;
    })

    const localMockState:MDMStore = {
      allMasters:MasterData,
      masters:updatedMasterData,
      options:[],
      selectedOptions:[],
      activeMaster:{id:1,fields:MasterData[0].fields,filters:MasterData[0].filters,progress:'submitted',name:MasterData[0].name,colDefs:mapMasterToColumnDefs(MasterData[0].fields),rowData:[],isChecked:true},
      isSelectMasterOpen:true,
      draftId:'',
      isUploadModalOpen:false,
      chunkSize:100,
      recordCount:0,
      isDataAvailableLocally:true,
      lastRunDate:''
    }

    const localMockStore = createStore(localMockState);

    render(contextWrapper(<VFTab {...props}/>,localMockStore))

    const tabsList = screen.getAllByTestId('tab-button');

    expect(tabsList[0]).toHaveStyle('background:#CECBCD 0% 0% no-repeat padding-box')

    const tabCloseBtn = screen.getAllByTestId('tab-close')[0];

    fireEvent.click(tabCloseBtn);

  });

  
});
