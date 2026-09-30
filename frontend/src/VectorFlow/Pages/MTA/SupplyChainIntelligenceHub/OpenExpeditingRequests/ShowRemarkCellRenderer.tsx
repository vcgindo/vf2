import { BPRRemarksCellRendererWrapper,BPRColorCellRendererIcon } from "../BPR/styles";

const ShowRemarkCellRenderer = (params:any)=>{

   
    return (
        <BPRRemarksCellRendererWrapper >
            <BPRColorCellRendererIcon 
            alt="history icon"
             src="/assets/img/VectorFLOW/BPR/history.svg"
             ref={(ref) => {
                if (!ref) return;
        
                ref.onclick = (e:any) => {
                 params.onClick(e, params.data)
                  e.stopPropagation();
                };
              }}
             />
        </BPRRemarksCellRendererWrapper>
    )
}


export default ShowRemarkCellRenderer