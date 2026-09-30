import {
    PercentBorderContainer,
    Percentborder,
    Percent,
    BtnGroup,
    Btns,
    ViewOrder,
    TextOnBox,
    ColorOnLeft,
    Separator,
    ButtonImg,
    TextOnColor,
    ImgDiv,
    ColoronLeftWrapper
} from '../MaterialSOBox/styles';
import { MaterialCoverageString } from '../../../../../VectorFlow/Pages/MTO/Common/String';
import Tooltip from '../../../../../VectorFlow/Pages/MTO/Common/Tooltip';
import { getToolTipContent, formatNumber } from '../../../../../VectorFlow/Pages/MTO/Procurement/MaterialCoverage/CommonFunc'
import { useUserData } from '../../../../../context';

interface MaterialSOProps {
    kit: string,
    colors: any,
    height: string,
    text: string,
    orderCount: number,
    cutCount: number,
    orderValue: number,
    percent: number,
    ToolTipdata?: any,
}

const MTOMaterialSO = ({ kit, colors, height, text, orderCount, cutCount, orderValue, percent, ToolTipdata }: MaterialSOProps) => {

    const formatPercent = (percent: number): string => {
        // Check if percent is NaN or 0, and return "NA" if true

        if (isNaN(percent) || percent === 0) {
            return 'NA';
        }

        // Perform the rounding operation if percent is not NaN or 0
        return `${Math.round(percent * 100).toString()}%`;
    };
     
    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;


    return (
        <>
            {
                colors.c1 == '#000' || colors.c2 == '#E53F40' || colors.c3 == '#EBBF2B' ?
                    <Tooltip tooltipZoom={1} zoom="1" content={getToolTipContent('Red', ToolTipdata)} >
                        <ColoronLeftWrapper>
                            <ColorOnLeft
                                color={colors.c1} height={height}>
                            </ColorOnLeft>
                            <ColorOnLeft
                                color={colors.c2} height={height}>
                            </ColorOnLeft>
                            <ColorOnLeft
                                color={colors.c3} height={height}>
                            </ColorOnLeft>
                        </ColoronLeftWrapper>
                    </Tooltip>
                    :
                    colors.c1 == '#418D18' ?
                        <Tooltip tooltipZoom={1} content={getToolTipContent('Green', ToolTipdata)} >
                            <ColoronLeftWrapper>
                                <ColorOnLeft
                                    color={colors.c1} height={height}>
                                </ColorOnLeft>
                            </ColoronLeftWrapper>

                        </Tooltip>
                        :
                        <Tooltip tooltipZoom='1' content={getToolTipContent('Blue', ToolTipdata)}>
                            <ColorOnLeft
                                color={colors.c1} height={height}>
                                <TextOnColor style={{
                                    position: 'absolute',
                                    left: '50%',
                                    fontSize: '8px',
                                    top: '50%',
                                    transform: 'translate(-50%, -50%) rotate(-90deg)',
                                    width: '100%',
                                }}>
                                    {text}
                                </TextOnColor>
                            </ColorOnLeft>
                        </Tooltip>
            }


            <TextOnBox>
                <ImgDiv>
                    {
                        kit === "No Kit" ?
                            <img src='/assets/img/NoKit2x.png' height='13px' width='15px' alt="Logo" />
                            :
                            kit === "Partial Kit" ?
                                <img src='/assets/img/PartialKit.png' height='7px' width='26px' alt="Logo" />
                                :
                                <img src='/assets/img/FullKit2x.png' height='17px' width='17px' alt="Logo" />
                    }
                </ImgDiv>
                <ImgDiv>
                    {
                        kit === "No Kit" ? "No Kit" : kit === "Partial Kit" ? "Partial Kit" : "Full Kit"
                    }
                </ImgDiv>
            </TextOnBox>


            <PercentBorderContainer>
                <Percentborder>
                    <Percent>{formatPercent(percent)}</Percent>
                </Percentborder>
            </PercentBorderContainer>

            <ViewOrder theme={themeUi}>
                {MaterialCoverageString.viewAllRecords}
            </ViewOrder>


            <BtnGroup>
                <Btns>
                    <Tooltip tooltipZoom='1' content={<div style={{ fontSize: '10px', padding: "10px 5px 10px 5px" }}>Order Count</div>} >
                        <ButtonImg
                            src='/assets/img/order-tracking.png'
                            height='15px' width='15px'
                        />
                    </Tooltip>
                    <p style={{ paddingLeft: '4px' }}>
                        {orderCount}
                    </p>
                </Btns>

                <Separator color={'grey'} ></Separator>
                <Btns>
                    <Tooltip tooltipZoom='1' content={<div style={{ fontSize: '10px', padding: "10px 5px 10px 5px" }}>No of Customer</div>} >
                        <ButtonImg
                            src='/assets/img/people.png'
                            height='15px' width='15px'
                        >
                        </ButtonImg>
                    </Tooltip>
                    <p style={{ paddingLeft: '4px' }}>
                        {cutCount}
                    </p>
                </Btns>

                <Separator color={'grey'} ></Separator>

                <Btns>
                    <Tooltip tooltipZoom='1' content={<div style={{ fontSize: '10px', padding: "10px 5px 10px 5px" }}>Order Value</div>} >
                        <ButtonImg
                            src='/assets/img/rupee.png'
                            height='15px' width='15px'
                        >
                        </ButtonImg>
                    </Tooltip>
                    <p style={{ paddingLeft: '4px' }}>
                        {formatNumber(orderValue)}
                    </p>
                </Btns>
            </BtnGroup>
        </>
    )
}

export default MTOMaterialSO;