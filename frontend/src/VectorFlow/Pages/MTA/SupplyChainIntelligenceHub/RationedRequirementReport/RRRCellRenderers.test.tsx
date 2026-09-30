
import {RRRTechColorCellRenderer,RRREcoColorCellRenderer,RRRDispatchColorCellRenderer} from './RRRCellRenderers';


window.URL.createObjectURL = jest.fn();

  
describe("Renders RRR Component", ()=>{

        
    
    it("Renders Dispacth Color Cell Renderer", async()=>{
        RRRDispatchColorCellRenderer({data:{DispatchColor:'Red'}})   
        RRRDispatchColorCellRenderer({data:{DispatchColor:'White'}})   
        RRRDispatchColorCellRenderer({data:{DispatchColor:'Green'}})   
        RRRDispatchColorCellRenderer({data:{DispatchColor:'Yellow'}})   
        RRRDispatchColorCellRenderer({data:{DispatchColor:'Black'}})  
        RRRDispatchColorCellRenderer({data:{DispatchColor:''}})    
  
    })

    it("Renders tech. Color Cell Renderer", async()=>{
        RRRTechColorCellRenderer({data:{TCol:'Red'}})   
        RRRTechColorCellRenderer({data:{TCol:'White'}})   
        RRRTechColorCellRenderer({data:{TCol:'Green'}})   
        RRRTechColorCellRenderer({data:{TCol:'Yellow'}})   
        RRRTechColorCellRenderer({data:{TCol:'Black'}})  
        RRRTechColorCellRenderer({data:{TCol:''}})    
  
    })

    it("Renders Eco. Color Cell Renderer", async()=>{
        RRREcoColorCellRenderer({data:{ECol:'Red'}})   
        RRREcoColorCellRenderer({data:{ECol:'White'}})   
        RRREcoColorCellRenderer({data:{ECol:'Green'}})   
        RRREcoColorCellRenderer({data:{ECol:'Yellow'}})   
        RRREcoColorCellRenderer({data:{ECol:'Black'}})  
        RRREcoColorCellRenderer({data:{ECol:''}})    
  
    })
})