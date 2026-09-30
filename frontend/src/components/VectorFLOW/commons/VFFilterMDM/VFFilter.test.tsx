import { render, fireEvent,waitFor } from '@testing-library/react';
import VFFilter from '.';
import {select} from 'react-select-event'
import { store } from '../../../../redux/store/store';
import { Provider } from 'react-redux';
import React,{ ReactNode } from 'react';
import { UserDataContext } from '../../../../context';

// Mock the onClick function
const onDelete = jest.fn();

const contextWrapper = (children:ReactNode,theme:string) => {
    return(
      <Provider store={store}>
            <UserDataContext.Provider
            value={{
              user: { user: { theme_ui: theme } },
              changeColorTheme: (color) => {
                return color;
              },
              isSideBarOpen:true,toggleSideBar:jest.fn
            }}
          >
            {children}
          </UserDataContext.Provider>
      </Provider>
        
    )
  }


const operators = [
    {
        label:'Equals to',
        value:'equals to'
    },
    {
        label:'Less than',
        value:'less than'
    }
]

const fields = [
    {
        label:'SKUName',
        value:'SKUName'
    },
    {
        label:'Quantity',
        value:'Quantity'
    }
]

const filters = [
    {
        id:'fbaksbfka',
        masterId:2,
        field:"",
        operator:"",
        text:''
    },
    {
        id:'generateRandomId()',
        field:"",
        masterId:2,
        operator:"",
        text:''
    },
    {
        id:'fkljsanfla',
        field:"",
        masterId:3,
        operator:"",
        text:''
    }
]

const currFilter = {
    field:'',
    operator:'',
    text:'',
    id:'fbaksbfka',
    masterId:1
}
const isDisabled = false;
const props = {
    operators,
    fields,
    onDelete,
    currFilter,
    filters,
    isDisabled
}

describe('Filter Component', () => {
  it('renders the component', () => {
    const { getByTestId } = render(contextWrapper(<VFFilter {...props}/>,"NOIRFUSION"));
    
    const filter = getByTestId('vffilter-wrapper');
    
    expect(filter).toBeInTheDocument();
  });

  it('calls the onDelete function when the delete icon is clicked',()=>{
    const {getByTestId} = render(contextWrapper(<VFFilter {...props}/>,"REGALBLAZE"));

    const deleteIcon = getByTestId('delete-icon')

    fireEvent.click(deleteIcon)
    expect(onDelete).toBeCalled()
  })

  it('selects the field when the select component is triggered',async()=>{
    const {getAllByRole} = render(contextWrapper(<VFFilter {...props} />,"CHARCOALCHIC"))
    await waitFor(async () => {
        const reactSelect = getAllByRole('combobox')[0]
        expect(reactSelect).toBeInTheDocument();
        await select(reactSelect, ['SKUName']);
      });
  })

  it('selects the operator when the select component is triggered',async()=>{
    const {getAllByRole} = render(contextWrapper(<VFFilter {...props}/>,"PUREELEGANCE"));
    await waitFor(async () => {
        const reactSelect = getAllByRole('combobox')[1]
        expect(reactSelect).toBeInTheDocument();
        await select(reactSelect, ['Equals to']);
      });
  })

  it('text field calls the onChange function when text is changed',async()=>{
    const {getByTestId} = render(contextWrapper(<VFFilter {...props}/>,"RANDOm"))
    const textInput = getByTestId('text-input')
    fireEvent.change(textInput,{target: {value: 'a'}})
  })

  // it('selects an option in the React Select component', async () => {
  //   const { getAllByRole } = render(contextWrapper(<VFFilter {...props} />));
    
  //   await waitFor(() => {
  //       const reactSelect = getAllByRole('combobox')[0]; // Assuming the React Select component is the first one in the component
  //       expect(reactSelect).toBeInTheDocument();
        
        
  //   })
  //   })

});