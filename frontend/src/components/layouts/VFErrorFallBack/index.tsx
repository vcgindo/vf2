// import VFButton from "../../VectorFLOW/commons/VFButton"
import { Player } from '@lottiefiles/react-lottie-player'
import { VFErrorFallBackHeader, VFErrorFallBackWrapper,VFErrorFallBackContainer,VFErrorFallBackButtonGroup, VFErrorFallBackTextContent, VFErrorFallBackButton,VFErrorFallBackButtonGhost } from "./styles"



const VFErrorFallBack = ()=>{




    const handleGoHome =()=>{
        window.location.href = '/landing-page'
    }

    const handleRefresh = ()=>{
        window.location.reload()
    }

    return(
        <VFErrorFallBackWrapper>
            <VFErrorFallBackContainer>
                <Player src={"/assets/img/VectorFLOW/BPR/CoffeeSpiling.json"} style={{height:280 }} loop autoplay/>
                <VFErrorFallBackHeader>Oops, Something Went Wrong!!!</VFErrorFallBackHeader>
                <VFErrorFallBackTextContent>
                    We are working on this and it might take some time <br/>You can <b>Refresh</b> or <b>Go Back to Home</b>.
                </VFErrorFallBackTextContent>
                <VFErrorFallBackButtonGroup>
                    <VFErrorFallBackButton themeUi={''} onClick={handleRefresh}  >
                        Refresh Now
                    </VFErrorFallBackButton>
                    <div style={{height:10}}/>
                    <VFErrorFallBackButtonGhost onClick={handleGoHome}>
                        Go back to home
                    </VFErrorFallBackButtonGhost>
                    {/* <VFButton themeUi="NOIRFUSION" onClick={()=>console.log('')} width={150}>
                        Contact Support
                    </VFButton> */}
                </VFErrorFallBackButtonGroup>
            </VFErrorFallBackContainer>
        </VFErrorFallBackWrapper>
    )
}

export default VFErrorFallBack