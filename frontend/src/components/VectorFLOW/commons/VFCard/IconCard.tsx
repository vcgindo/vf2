
import {  IconCardContainer, CardText ,CardIconWrapper} from "./styles"


interface IconCardProps{
    text:string
    iconOnMouseIn:string
    iconOnMouseOut:string
    onClick:()=>void
    themeUi:string
}


const IconCard = (props:IconCardProps)=>{


    const {
        iconOnMouseOut,
        text,
        onClick,
        themeUi
    } = props


    return(
        <IconCardContainer imgSrc="/assets/img/VectorFLOW/NMS/card-bg.svg" onClick={onClick} data-testid={"icon-card"}>
            <CardText themeUi={themeUi} onClick={onClick} data-testid={"icon-card"}>{text}</CardText>
            <CardIconWrapper >
                <img data-testid='icon' src={iconOnMouseOut}/>
            </CardIconWrapper>
        </IconCardContainer>
    )
}

export default IconCard