import { Player } from "@lottiefiles/react-lottie-player"
import { useUserData } from "../../../../context"
import { SCLoaderContainer } from "../../layouts/SelectMaster/styles"

const VFLoader = ({styles}: any)=>{
    // return(
    //     <SCLoaderContainer>
    //         <img src="/assets/img/VectorFLOW/loaderBig.svg" data-testid="loader"/>
    //     </SCLoaderContainer>
    // )

    const {user} = useUserData()
    const themeUi = user?.user?.theme_ui || "";
    return(
        <SCLoaderContainer data-testid="loader">
            <Player src={themeUi==="REGALBLAZE"?'/assets/img/VectorFLOW/BPR/Grid LoaderRoyalBlue.json':'/assets/img/VectorFLOW/BPR/Grid Loader.json'} loop autoplay style={styles ? {...styles} : {height:'200px',width:'200px'}}/>
        </SCLoaderContainer>
    )
}

export default VFLoader