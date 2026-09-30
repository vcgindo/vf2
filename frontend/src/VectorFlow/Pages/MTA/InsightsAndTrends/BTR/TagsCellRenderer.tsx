import { useUserData } from '../../../../../context';
import {BPRTagsCellRendererWrapper} from '../../SupplyChainIntelligenceHub/BPR/styles'

 const TagsCellRenderer = (params:any)=>{
    const { user } = useUserData();
    
    if(!params.value ||  params.value.length<1)return null
    return(
        <BPRTagsCellRendererWrapper theme={user.user.theme_ui} style={{height:18,padding:"0px 3px",fontSize:9,width:55}}>
            {params.value}
        </BPRTagsCellRendererWrapper>
    )
}

export default TagsCellRenderer;