
import { useUserData } from "../../../../context"
import { VFCapsuleButton, VFCapsuleWrapper } from "./styles"

interface Capsule{
    label:string
    value:string
}

interface VFCapsuleProps{
    activeBtn:Capsule
    capsules:Capsule[]
    handleClick:any
}

const VFCapsule = (props:VFCapsuleProps)=>{

    const {
        activeBtn,
        capsules,
        handleClick
    } = props

    

    const {user} = useUserData()


    const onClick = (capsule:Capsule)=>{
        handleClick(capsule)
        
    }

    const activeCapsule = activeBtn 

    return(
        <VFCapsuleWrapper themeUi={user.user.theme_ui} data-testid = 'vf-capsule'>
            {capsules.map((c:Capsule)=>{
                return(
                    <VFCapsuleButton isActive={c.value===activeCapsule.value} onClick={()=>onClick(c)} themeUi={user.user.theme_ui} key={c.value}>
                        {c.label}
                    </VFCapsuleButton>
                )
            })}
        </VFCapsuleWrapper>
    )
}

export default VFCapsule