import Tooltip from "../../../VectorFLOW/commons/MTO/Tooltip";
import { SCButton, TooltipText } from "./styles"
import React, { CSSProperties, ReactNode } from 'react';

interface VFButtonProps {
    onClick: any ,
    themeUi: string,
    disabled?: boolean,
    width?: number,
    children: React.ReactNode,
    style?: CSSProperties,
    onHoverChild?: ReactNode,
    currentStep?: number
}

const VFButton = (props: VFButtonProps) => {

    const {
        onClick,
        themeUi,
        disabled,
        width,
        style,
        children,
        currentStep
    } = props

    const getChildren = () => {
        // if(onHoverChild){
        //     if(hoverState){
        //         return onHoverChild
        //     }
        // }
        return children
    }

    return (
        <>
            {disabled && currentStep == 2 ?
                <Tooltip content={<TooltipText>{"Assign a route and apply the production buffer to all the orders!"}</TooltipText>}>
                    <SCButton onClick={onClick} themeUi={themeUi} isDisabled={disabled} customWidth={width} style={style} data-testid="vf-button">
                        {getChildren()}
                    </SCButton>
                </Tooltip >
                : <SCButton onClick={onClick} themeUi={themeUi} isDisabled={disabled} customWidth={width} style={style} data-testid="vf-button">
                    {getChildren()}
                </SCButton>
            }
        </>
    )
}

export default VFButton;