import { Player } from '@lottiefiles/react-lottie-player'
import React from 'react'
import VFOverlay from '../../../../../components/VectorFLOW/commons/VFOverlay'
import {useUserData} from '../../../../../context'

interface Props {
    message?: string
}
const OverlayLoader = ({ message }: Props) => {
    
    const { user } = useUserData();
    const themeUi = user.user.theme_ui;

    return (
        <VFOverlay>
            {/* <h1 >{message ? message : 'Loading....'}</h1> */}
            <div style={{ backgroundColor: "white", padding: '15px', borderRadius: '8px', display: "flex", flexDirection:"column", alignItems:"center" }}>
            <Player src={themeUi==="REGALBLAZE"?'/assets/img/VectorFLOW/BPR/Grid LoaderRoyalBlue.json':'/assets/img/VectorFLOW/BPR/Grid Loader.json'} loop autoplay style={{height:'200px',width:'200px'}}/>
                {message}
            </div>
        </VFOverlay>
    )
}

export default OverlayLoader