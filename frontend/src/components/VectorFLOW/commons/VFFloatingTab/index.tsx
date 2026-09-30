import { useEffect, useState } from 'react'
import { useUserData } from '../../../../context'
import {VFFloatingTabWrapper,VFFloatingTabButton,VFFloatingTabButtonActiveShadow} from './styles'
import { CSSProperties } from 'styled-components'

export interface VFFloatingTabItemProps{
    label:string
    value:string
    id: string
}


export interface VFFloatingTabProps{
    tabs:Array<VFFloatingTabItemProps>
    defaultTab?:number
    handleClick?: (i: any) => void  
    style?: CSSProperties
}

interface ActiveShadowDataType{
    width:number | string | undefined,
    left:number | string | undefined
}

const VFFloatingTab = (props:VFFloatingTabProps)=>{

    const {
        tabs,
        defaultTab=0,
        handleClick,
        style
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui
    
    const [activeIndex,setActiveIndex] = useState<number>(defaultTab)

    const [activeShadowData,setActiveShadowData] = useState<ActiveShadowDataType | null>(null)

    useEffect(()=>{
        const activeTabElement = document.getElementById(tabs[defaultTab].id)
        setActiveShadowData({
            left:activeTabElement?.offsetLeft,
            width:activeTabElement?.offsetWidth
        })
       
    },[])
   

    const onClick = (e:any,index:number)=>{
        setActiveShadowData({
            left:e.currentTarget.offsetLeft,
            width:e.currentTarget.offsetWidth
        })
        setActiveIndex(index)
       if( handleClick) handleClick(tabs[index])
    }

    return(
        <VFFloatingTabWrapper>
            {tabs.map((t:VFFloatingTabItemProps,index:number)=>{
                return(
                    <VFFloatingTabButton
                        id={t.id}
                        isActive={index===activeIndex}
                        key={index}
                        onClick={(e)=>onClick(e,index)}
                        data-testid='floatingTabButton'
                        style={style}
                    >
                        {t.label}
                    </VFFloatingTabButton>
                )
            })}
            {activeShadowData && <VFFloatingTabButtonActiveShadow theme={themeUi} style={{left:activeShadowData.left,width:activeShadowData.width}}/>}
        </VFFloatingTabWrapper>
    )
}

export default VFFloatingTab