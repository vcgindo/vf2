import VFButtonOutline from "../../../VectorFLOW/commons/VFButtonOutline";
import { ContentWrapper, TextContainer, TextFilterWrapper,VFMasterGroupCard,VFMasterGroupCardHeader,VFMasterGroupCardHeaderText, VFButtonWrapper,VFMasterGroupCardContent,VFMasterGroupCardImage,VFMasterGroupCardText,VFMasterGroupCardContainer} from "./styles"
import { useUserData } from "../../../../context";
import VFButton from "../../../VectorFLOW/commons/VFButton";
import { useState,ReactNode} from "react";
import { MDMMasterState, Option } from "../../../../VectorFlow/types/MDM";
import {ImageMapper,ImageMapperHover, masterGroupMapper} from "../../../../helpers/MDMConstants"
import VFMasterFieldSearch from "../../commons/VFMasterFieldSearch";
import * as globalStyles from "../../../../styles/global";
import { useDispatch } from "react-redux";
import { FILL_SELECTED_OPTIONS } from "../../../../redux/actions/MDM";

export interface SelectGroupedMastersProps {
    onSubmit:()=>void;
    onCancel:()=>void;
    onHover?:ReactNode;
    handleOnClickMaster:(master:MDMMasterState)=>void;
    allMasters:MDMMasterState[]
    selectedMasters:MDMMasterState[]
    text:string
    shouldShowMasterGroup:any
    shouldShowMaster:any
    options:Array<Option>
    selectedOptions:Array<Option>,
    isAdd?:boolean
}
interface CardProps{
    master:MDMMasterState
    handleOnClickMaster:(master:MDMMasterState)=>void
    selectedMasters:MDMMasterState[]
}

const Card=(props:CardProps)=>{
    const {user} = useUserData()
    const [isHovered, setIsHovered] = useState(false);
    const {
        master,
        handleOnClickMaster,
        selectedMasters
    } = props;

    const getMasterName = ():string=>{
        if(master.id==11 || master.id==12){
            return "Seasonality"
        }
        if(master.id==7 || master.id==8 || master.id==9){
            return 'Phase In Phase Out'
        }
        return master.name
    }

    const doesMasterExist = ()=>{
        if(master.id==7){
            return selectedMasters.find((m)=>m.id==7 || m.id==8 || m.id==9)
        }
        if(master.id==11){
            return selectedMasters.find((m)=>m.id==11 || m.id==12)
        }
        return selectedMasters.find((m)=>m.id==master.id)
    }

    return(
        <VFMasterGroupCardContent data-testid='vf-master-group-card' theme={user.user.theme_ui} style={{backgroundColor: doesMasterExist()|| isHovered ? user.user.theme_ui==="REGALBLAZE"?"rgb(252, 163, 17,0.3)":'#FCE7F2': 'white'}}
            id={master.name} 
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            onClick={()=>handleOnClickMaster(master)}
        >
            <VFMasterGroupCardImage data-testid="vf-master-card-image"
                style={{ 
                    backgroundColor:doesMasterExist() || isHovered ? globalStyles.chooseThemeColor[user.user.theme_ui]?.color5 : '#F4F4F4',
                    border:doesMasterExist() || isHovered ? 'white 1px solid':'none'
                }}>
                <img src={isHovered || doesMasterExist()
                    ?ImageMapperHover[master.id]
                    :ImageMapper[master.id]
                    }
                    alt={master.name}
                    height='37px'
                    width='37px'
                />
            </VFMasterGroupCardImage>
            <VFMasterGroupCardText style={{color:doesMasterExist() || isHovered ? 'white': 'black'}}>
                <div key={master.name}>
                <p style={{color:'black'}}>{getMasterName()}</p>
                </div>
            </VFMasterGroupCardText>
        </VFMasterGroupCardContent>
    )
}

const SelectGroupedMasters = (props:SelectGroupedMastersProps)=>{   
    const{
        onSubmit,
        onCancel,
        handleOnClickMaster,
        allMasters,
        selectedMasters,
        text,
        shouldShowMasterGroup,
        shouldShowMaster,
        selectedOptions,
        options,
    } = props

    const {user} = useUserData();

    const dispatch = useDispatch()

    const handleClick = (data:any)=>{
        dispatch(FILL_SELECTED_OPTIONS(data))
    }

    function removeFromSelectedMaster(valueToRemove:any) {
        let currentUrl = window.location.href;
        const paramName = 'selectedMaster';
        
        const regex = new RegExp(`[?&]${paramName}=([^&]*)`);
        const match = currentUrl.match(regex);
        
        if (match) {
            let currentValues = match[1].split(',');
            currentValues = currentValues.filter(value => value !== valueToRemove);
            
            const newParamString = currentValues.length ? `${paramName}=${currentValues.join(',')}` : '';
            if (newParamString) {
                currentUrl = currentUrl.replace(regex, `${match[0][0]}${newParamString}`);
            } else {
                currentUrl = currentUrl.replace(regex, '');
                currentUrl = currentUrl.replace(/([?&])$/, '');
            }
            window.history.replaceState(null, '', currentUrl);
        }
    }

    function addToSelectedMaster(masterId: any) {
        const currentUrl = window.location.href;
        const paramName = 'selectedMaster';
        

        
        const baseUrl = currentUrl.split('?')[0];
        let newUrl = currentUrl;
        
        const regex = new RegExp(`[?&]${paramName}=([^&]*)`);
        const match = currentUrl.match(regex);
        
        if (match) {
            let queryParams = match[1];
            
            // Split and check the existing IDs
            const queryParamsArray = queryParams.split(',');
            if (!queryParamsArray.includes(masterId)) {
                queryParamsArray.push(masterId);
            }
    
            queryParams = queryParamsArray.join(',');
            newUrl = baseUrl + '?' + paramName + '=' + queryParams;
        } else {
            if (!currentUrl.includes('?')) {
                newUrl = baseUrl + '?' + paramName + '=' + masterId;
            } else {
                newUrl = baseUrl + window.location.search + '&' + paramName + '=' + masterId;
            }
        }
        
        window.history.replaceState(null, '', newUrl);
    }
    

    const handleClickWrapper = (props:MDMMasterState)=>{

        const exists = selectedMasters.some((master)=>master.id === props.id)

            exists ? removeFromSelectedMaster(props.id) :  addToSelectedMaster(props.id) 
        handleOnClickMaster(props)
    }
   
 return(
    <ContentWrapper style={{zoom:'var(--default-zoom)'}}>
        <TextFilterWrapper>
            <TextContainer>
             <p>What kind of records do you want to {text}?</p>
            </TextContainer>
            <VFMasterFieldSearch 
                    value={selectedOptions} 
                    setValue={handleClick} 
                    options={options} 
                    placeholder={'Select'} 
                    handleListChild={()=>{return}} 
                    maxToShow={3} 
                    backgroundColor={'#FFFFFF'}
                    disabled={false}
                />
        </TextFilterWrapper>

        <VFMasterGroupCardContainer> 
        {
        masterGroupMapper.map(masterGroup=>{
         if(masterGroup.masters.length<1 )return 
            // console.log(masterGroup.name,shouldShowMaster(masterGroup))
           if(shouldShowMasterGroup(masterGroup)){
            return(
       
                <VFMasterGroupCard> 
    
                    <VFMasterGroupCardHeader>
                        <VFMasterGroupCardHeaderText> 
                            <p>{masterGroup.name}</p>
                        </VFMasterGroupCardHeaderText>
                           
                    </VFMasterGroupCardHeader>
                    <div className="custom-scrollbar" style={{ overflow:'auto', width:'100%', paddingLeft:'10px', paddingRight:'10px'}}>
    
                    {allMasters.map((currentMaster)=>{
                                if(shouldShowMaster(currentMaster) && masterGroup.masters.includes(currentMaster.id.toString())){
                                return(
                                <Card master={currentMaster} handleOnClickMaster={handleClickWrapper} selectedMasters={selectedMasters}/>
                            )}})} 
                                        </div>
    
                </VFMasterGroupCard>                             
    
    
                        )
           }

            })
        }

           

        </VFMasterGroupCardContainer> 

            <VFButtonWrapper>
                <VFButtonOutline onClick={onCancel} themeUi={user.user.theme_ui} style={{marginRight:'25px'}}>Cancel</VFButtonOutline>
                <VFButton onClick={onSubmit} themeUi={user.user.theme_ui} disabled={selectedMasters.length===0}>Submit</VFButton>
            </VFButtonWrapper> 
    </ContentWrapper>

    )
}


export default SelectGroupedMasters;

