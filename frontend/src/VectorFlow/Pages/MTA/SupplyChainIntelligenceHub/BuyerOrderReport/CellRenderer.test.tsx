
import {DispatchColorCellRenderer} from './CellRenderer';

  window.URL.createObjectURL = jest.fn();

  
describe("Renders BOR Component", ()=>{

        
    
    it("Renders Dispacth Color Cell Renderer", async()=>{
        DispatchColorCellRenderer({data:{DispatchColor:'Red'}})   
        DispatchColorCellRenderer({data:{DispatchColor:'White'}})   
        DispatchColorCellRenderer({data:{DispatchColor:'Green'}})   
        DispatchColorCellRenderer({data:{DispatchColor:'Yellow'}})   
        DispatchColorCellRenderer({data:{DispatchColor:'Black'}})  
        DispatchColorCellRenderer({data:{DispatchColor:''}})    
  
    })
})

