import { SCButtonOutline } from "./styles"
import React,{CSSProperties, ReactNode} from 'react';

interface VFButtonOutlineProps{
    onClick:() => void,
    themeUi:string,
    disabled?:boolean,
    width?:number,
    color?:string,
    onHoverChild?:ReactNode
    children:React.ReactNode
    style?:CSSProperties
    //isHoverDisabled?:boolean

}

const VFButtonOutline = (props:VFButtonOutlineProps)=>{
    

    const {
        onClick,
        themeUi,
        disabled,
        width,
        children,
        color,
        style,
      
    } = props

    //const [hoverState,setHoverState] = useState(false);
    
    const getChildren = ()=>{
        // if(onHoverChild){
        //     if(hoverState){
        //         return onHoverChild
        //     }
        // }
        return children
    }

    return(
        <SCButtonOutline color={color} 
        onClick={onClick} 
        themeUi={themeUi} 
        isDisabled={disabled} 
        customWidth={width} 
        hoverState={false} 
        style={style}
        
        // onMouseOver={props.isHoverDisabled ? undefined : () => setHoverState(true)}
        //onMouseOut={props.isHoverDisabled ? undefined : () => setHoverState(false)} 
        data-testid="vf-button-outline">
            {getChildren()}
        </SCButtonOutline>
    )
}

export default VFButtonOutline;

