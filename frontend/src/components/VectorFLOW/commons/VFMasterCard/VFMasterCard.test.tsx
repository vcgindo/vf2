

import { fireEvent, render, screen } from '@testing-library/react';
import { Master } from '../../../../VectorFlow/types/MDM';
import MRCard from '.';

const sampleData:Master = {
  id: 1,
  name: 'Sample Card',
  fields: [
    {
      displayName:'SKU Name'
      ,key:'sku_name'
      ,visible:true,
      isAdd:true,
      isDownload:true,
      isEdit:true,
      "col_Position":'1',
      "isApplicable":true,
      dataType:'String'
    },
    {
      displayName:'City'
      ,key:'city'
      ,visible:true,
      isAdd:true,
      isDownload:true,
      isEdit:true,
      "col_Position":'1',
      "isApplicable":true,
      dataType:'String'
    },
    {
      displayName:'MRP'
      ,key:'mrp'
      ,visible:true,
      isAdd:true,
      isDownload:true,
      isEdit:true,
      "col_Position":'1',
      "isApplicable":true,
      dataType:'String'
    }
  ]
};

const selectedFields = ['SKU Name']
const selectedColor = 'rgba(188, 61, 129, 0.302)'; 

describe('MRCard Component', () => {
  it('renders card header with the correct name', () => {
    render(<MRCard data={sampleData} selectedFields={selectedFields} isSelected={false} onSelectCheckbox={()=>console.log('')} isCheckBoxDisabled={true} themeUi={'NOIRFUSION'}/>);
    const cardHeader = screen.getByText('Sample Card');
    expect(cardHeader).toBeInTheDocument();
  });


  it('renders card list items with the correct titles', () => {
    render(<MRCard data={sampleData} selectedFields={selectedFields} isSelected={false} onSelectCheckbox={()=>console.log('')} isCheckBoxDisabled={true} themeUi={'NOIRFUSION'} />);
    const field1 = screen.getByText('SKU Name');
    const field2 = screen.getByText('City');
    const field3 = screen.getByText('MRP');
    
    expect(field1).toBeInTheDocument();
    expect(field2).toBeInTheDocument();
    expect(field3).toBeInTheDocument();
  });

  it('applies "isSelected" background color to selected fields', () => {
    render(<MRCard data={sampleData} selectedFields={selectedFields} isSelected={false} onSelectCheckbox={()=>console.log('')} isCheckBoxDisabled={true} themeUi={'NOIRFUSION'}/>);

    const field1 = screen.getByText('SKU Name');
    const field2 = screen.getByText('City');
    const field3 = screen.getByText('MRP');
    
   

    expect(getComputedStyle(field1).backgroundColor).toBe(selectedColor);
    expect(getComputedStyle(field2).backgroundColor).not.toBe(selectedColor);
    expect(getComputedStyle(field3).backgroundColor).not.toBe(selectedColor);
  });

  it('handles empty selectedFields', () => {
    render(<MRCard data={sampleData} selectedFields={[]} isSelected={false} onSelectCheckbox={()=>console.log('')} isCheckBoxDisabled={true} themeUi={'NOIRFUSION'} />);
    const field1 = screen.getByText('SKU Name');
    const field2 = screen.getByText('City');
    const field3 = screen.getByText('MRP');


    expect(getComputedStyle(field1).backgroundColor).not.toBe(selectedColor);
    expect(getComputedStyle(field2).backgroundColor).not.toBe(selectedColor);
    expect(getComputedStyle(field3).backgroundColor).not.toBe(selectedColor);
  });

  it('handles empty data fields', () => {
    const emptyData = {
      id: 1,
      name: 'Empty Card',
      fields: [],
    };
    const {getByTestId} = render(<MRCard data={emptyData} selectedFields={selectedFields} isSelected={false} onSelectCheckbox={()=>console.log('')} isCheckBoxDisabled={true} themeUi={'NOIRFUSIONs'}/>);
    
    expect(getByTestId('list-container').children.length).toBe(0)
    
  });

  it("handles themeui", ()=>{
    render(<MRCard data={sampleData} selectedFields={[]} isSelected={false} onSelectCheckbox={()=>console.log('')} isCheckBoxDisabled={false} themeUi={'REGALBLAZE'} />);
    const btn=screen.getAllByTestId('check-box')[0]
    expect(btn).toBeInTheDocument()
    fireEvent.click(btn)
    fireEvent.click(btn)
   });

   it("handles themeui", ()=>{
    render(<MRCard data={sampleData} selectedFields={[]} isSelected={false} onSelectCheckbox={()=>console.log('')} isCheckBoxDisabled={false} themeUi={'NOIRFUSION'} />);
    const btn=screen.getAllByTestId('check-box')[0]
    expect(btn).toBeInTheDocument()
    fireEvent.click(btn)
    fireEvent.click(btn)
   });
   
  })

//   it('Handles checkbox', async () =>{
//     render(<MRCard data={sampleData} selectedFields={[]} isSelected={false} onSelectCheckbox={()=>console.log('')} isCheckBoxDisabled={true} />);

//     const checkboxes = screen.getAllByRole('checkbox')
//     await waitFor(async () => {
//     checkboxes.forEach((checkbox:any)=>{
//         fireEvent.click(checkbox)
//     })
// })
// checkboxes.forEach((checkbox:any)=>{
//     fireEvent.change(checkbox, {target:{checked:false}})

// })
     


  // })
