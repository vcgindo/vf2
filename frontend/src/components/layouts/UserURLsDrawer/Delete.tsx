import { PrimaryButton, SecondaryButton } from "../../../components/commons/styled";
import { ButtonsWrapper, URLsForm } from "./styles";
import { useUserData } from "../../../context"

const DeleteUrl  = (props:{
    onSuccess:()=>void
    onFailure:()=>void
})=>{

    const {
        onFailure,
        onSuccess
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui


    return(
        <URLsForm>
        <h2 style={{fontSize:'18px',fontWeight:'400',textAlign:'center',flex:1}}>Are you sure you want to Delete ?</h2>
        <ButtonsWrapper style={{justifyContent:'flex-end',alignItems:'flex-end',flex:10}}>
            <SecondaryButton type="button" themeUi={themeUi} onClick={onFailure}>
                Cancel
            </SecondaryButton>
            <PrimaryButton type="button" themeUi={themeUi} onClick={onSuccess}>
                Confirm
            </PrimaryButton> 
        </ButtonsWrapper>
    </URLsForm>
    )
}

export default DeleteUrl