import { useEffect, useState } from 'react';
import {
    MainContainer,
    Box,
    Main,
} from './styles';
import { calculatePercentage, mapOrderDetails, DetailsObj, calculateColorOrderCount } from './CommonFunc';
import { ColorsMTO } from '../../Common/Colors';
import MTOMaterialSO from '../../../../../components/VectorFLOW/commons/MTO/MaterialSOBox/MTOMaterialSO';
import { useDispatch } from 'react-redux';
import { SAVE_ANALYTICS_DATA } from '../../../../../redux/actions/MTO/index';

interface CurrentCovProps {
    data: any,
    handleToggleComponent: any,
    setDetailDataObj: (data: DetailsObj) => void
}

interface useRedStateProps {
    Bnk: number,
    Bnkp: number,
    Bpk: number,
    Bpkp: number,
    Bfk: number,
    Bfkp: number,
    Rnk: number,
    Rnkp: number,
    Rpk: number,
    Rpkp: number,
    Rfk: number,
    Rfkp: number,
    Ynk: number,
    Ynkp: number,
    Ypk: number,
    Ypkp: number,
    Yfk: number,
    Yfkp: number,
    Gnk: number,
    Gnkp: number,
    Gpk: number,
    Gpkp: number,
    Gfk: number,
    Gfkp: number,
    Blnk: number,
    Blnkp: number,
    Wnk: number,
    Wnkp: number,
    Blpk: number,
    Blpkp: number,
    Wpk: number,
    Wpkp: number,
    Blfk: number,
    Blfkp: number,
    Wfk: number,
    Wfkp: number
}




const CurrentCov = ({ data: SOData, handleToggleComponent, setDetailDataObj }: CurrentCovProps) => {
    const dispatch = useDispatch();
    const [totalOrderCount, setTotalOrdeerCount] = useState<number>(0);
    const [totalBlueOrdCount, setTotalBlueOrdCunt] = useState<number>(0);

    const [colorOrderCount, setColorOrderCount] = useState<useRedStateProps>()


    const [BRYNkOrdCunt, setBRYNkOrdCunt] = useState<number>(0);
    const [BRYNkCustCunt, setBRYNkCustCunt] = useState<number>(0);
    const [BRYNkOrdVal, setBRYNkOrderVal] = useState<number>(0);

    const [secBlockOrdCnt, setSecBlockOrdCnt] = useState<number>(0);
    const [secBlockCustCnt, setSecBlockCustCnt] = useState<number>(0);
    const [secOrderVal, setsecOrderVal] = useState<number>(0);

    const [thrdBlockOrdCnt, setthrdBlockOrdCnt] = useState<number>(0);
    const [thrdBlockCustCnt, setthrdBlockCustCnt] = useState<number>(0);
    const [thrdOrderVal, setthrdOrderVal] = useState<number>(0);

    const [frthBlockOrdCnt, setfrthBlockOrdCnt] = useState<number>(0);
    const [frthBlockCustCnt, setfrthBlockCustCnt] = useState<number>(0);
    const [frthOrderVal, setfrthdOrderVal] = useState<number>(0);

    const [fifthBlockOrdCnt, setfifthBlockOrdCnt] = useState<number>(0);
    const [fifthBlockCustCnt, setfifthBlockCustCnt] = useState<number>(0);
    const [fifthOrderVal, setfifthdOrderVal] = useState<number>(0);

    const [sxthBlockCustCnt, setsxthBlockCustCnt] = useState<number>(0);
    const [sxthBlockOrdCnt, setsxthBlockOrdCnt] = useState<number>(0);
    const [sxthdOrderVal, setsxthdOrderVal] = useState<number>(0);

    const [svthBlockCustCnt, setsvthBlockCustCnt] = useState<number>(0);
    const [svthBlockOrdCnt, setsvthBlockOrdCnt] = useState<number>(0);
    const [svthdOrderVal, setsvthdOrderVal] = useState<number>(0);
    const [svthSrtDt, setSvthSrtDt] = useState<string>('');
    const [svthEndDt, setSvthEndDt] = useState<string>('');

    const [egthBlockCustCnt, setegthBlockCustCnt] = useState<number>(0);
    const [egthBlockOrdCnt, setegthBlockOrdCnt] = useState<number>(0);
    const [egthdOrderVal, setegthdOrderVal] = useState<number>(0);
    const [egthSrtDt, setegthSrtDt] = useState<string>('');
    const [egthEndDt, setegthEndDt] = useState<string>('');

    const [nthBlockCustCnt, setnthBlockCustCnt] = useState<number>(0);
    const [nthBlockOrdCnt, setnthBlockOrdCnt] = useState<number>(0);
    const [nthhdOrderVal, setnthhdOrderVal] = useState<number>(0);
    const [nthSrtDt, setnthSrtDt] = useState<string>('');
    const [nthEndDt, setnthEndDt] = useState<string>('');


    const loadInitialData = () => {

        const totalOrdCunt: any = calculatePercentage(SOData, ColorsMTO.Black.label, ColorsMTO.Red.label, ColorsMTO.Yellow.label, ColorsMTO.Green.label, 0);
        setTotalOrdeerCount(totalOrdCunt);

        const totalBlueOrdCount: any = calculatePercentage(SOData, ColorsMTO.Blue.label, ColorsMTO.White.label, "", "", 1);
        setTotalBlueOrdCunt(totalBlueOrdCount)

        const firstBlock: any = mapOrderDetails(SOData, ColorsMTO.Black.label, ColorsMTO.Red.label, ColorsMTO.Yellow.label, "NK", 0);
        setBRYNkCustCunt(firstBlock.cusCunt);
        setBRYNkOrdCunt(firstBlock.ordCunt);
        setBRYNkOrderVal(firstBlock.totalCunt);


        const secondBlock: any = mapOrderDetails(SOData, ColorsMTO.Black.label, ColorsMTO.Red.label, ColorsMTO.Yellow.label, "PK", 0);
        setSecBlockCustCnt(secondBlock.cusCunt);
        setSecBlockOrdCnt(secondBlock.ordCunt);
        setsecOrderVal(secondBlock.totalCunt);

        const thirdBlock: any = mapOrderDetails(SOData, ColorsMTO.Black.label, ColorsMTO.Red.label, ColorsMTO.Yellow.label, "FK", 0);
        setthrdBlockCustCnt(thirdBlock.cusCunt);
        setthrdBlockOrdCnt(thirdBlock.ordCunt);
        setthrdOrderVal(thirdBlock.totalCunt);

        const frthBlock: any = mapOrderDetails(SOData, ColorsMTO.Green.label, "", "", "NK", 0);
        setfrthBlockCustCnt(frthBlock.cusCunt);
        setfrthBlockOrdCnt(frthBlock.ordCunt);
        setfrthdOrderVal(frthBlock.totalCunt);

        const fifthBlock: any = mapOrderDetails(SOData, ColorsMTO.Green.label, "", "", "PK", 0);
        setfifthBlockCustCnt(fifthBlock.cusCunt);
        setfifthBlockOrdCnt(fifthBlock.ordCunt);
        setfifthdOrderVal(fifthBlock.totalCunt);

        const sxthBlock: any = mapOrderDetails(SOData, ColorsMTO.Green.label, "", "", "FK", 0);
        setsxthBlockCustCnt(sxthBlock.cusCunt);
        setsxthBlockOrdCnt(sxthBlock.ordCunt);
        setsxthdOrderVal(sxthBlock.totalCunt);

        const svnthBlock: any = mapOrderDetails(SOData, ColorsMTO.Blue.label, ColorsMTO.White.label, "", "NK", 1);
        setsvthBlockCustCnt(svnthBlock.cusCunt);
        setsvthBlockOrdCnt(svnthBlock.ordCunt);
        setsvthdOrderVal(svnthBlock.totalCunt);
        setSvthSrtDt(svnthBlock.stdt);
        setSvthEndDt(svnthBlock.endt)

        const egthBlock: any = mapOrderDetails(SOData, ColorsMTO.Blue.label, ColorsMTO.White.label, "", "PK", 1);
        setegthBlockCustCnt(egthBlock.cusCunt);
        setegthBlockOrdCnt(egthBlock.ordCunt);
        setegthdOrderVal(egthBlock.totalCunt);
        setegthSrtDt(egthBlock.stdt)
        setegthEndDt(egthBlock.endt)

        const nthBlock: any = mapOrderDetails(SOData, ColorsMTO.Blue.label, ColorsMTO.White.label, "", "FK", 1);
        setnthBlockCustCnt(nthBlock.cusCunt);
        setnthBlockOrdCnt(nthBlock.ordCunt);
        setnthhdOrderVal(nthBlock.totalCunt);
        setnthSrtDt(nthBlock.stdt)
        setnthEndDt(nthBlock.endt)


        const blackNK = calculateColorOrderCount(SOData, ColorsMTO.Black.label, 'NK', 0)
        const blackNKPercent = Math.round((blackNK / totalOrdCunt) * 100);

        const blackPK = calculateColorOrderCount(SOData, ColorsMTO.Black.label, 'PK', 0);
        const blackPKPercent = Math.round((blackPK / totalOrdCunt) * 100)


        const blackFK = calculateColorOrderCount(SOData, ColorsMTO.Black.label, 'FK', 0);
        const blackFKPercent = Math.round((blackFK / totalOrdCunt) * 100)

        const RedNK = calculateColorOrderCount(SOData, ColorsMTO.Red.label, 'NK', 0);
        const RedNKPercent = Math.round((RedNK / totalOrdCunt) * 100)

        const RedPK = calculateColorOrderCount(SOData, ColorsMTO.Red.label, 'PK', 0);
        const RedPKPercent = Math.round((RedPK / totalOrdCunt) * 100)

        const RedFK = calculateColorOrderCount(SOData, ColorsMTO.Red.label, 'FK', 0);
        const RedFKPercent = Math.round((RedFK / totalOrdCunt) * 100)

        const YellowNK = calculateColorOrderCount(SOData, ColorsMTO.Yellow.label, 'NK', 0);
        const YellowNKPercent = Math.round((YellowNK / totalOrdCunt) * 100)

        const YellowPK = calculateColorOrderCount(SOData, ColorsMTO.Yellow.label, 'PK', 0);
        const YellowPkPercent = Math.round((YellowPK / totalOrdCunt) * 100)

        const YellowFK = calculateColorOrderCount(SOData, ColorsMTO.Yellow.label, 'FK', 0);
        const YellowFkPercent = Math.round((YellowFK / totalOrdCunt) * 100)

        const GreenNK = calculateColorOrderCount(SOData, ColorsMTO.Green.label, 'NK', 0);
        const GreenNKPercent = Math.round((GreenNK / totalOrdCunt) * 100)


        const GreenPK = calculateColorOrderCount(SOData, ColorsMTO.Green.label, 'PK', 0);
        const GreenPKPercent = Math.round((GreenPK / totalOrdCunt) * 100)

        const GreenFK = calculateColorOrderCount(SOData, ColorsMTO.Green.label, 'FK', 0);
        const GreenFKPercent = Math.round((GreenFK / totalOrdCunt) * 100)


        const BlueNK = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'NK', 1);
        const BlueNKPercent = Math.round((BlueNK / svnthBlock.ordCunt) * 100)

        const WhiteNK = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'NK', 1);
        const WhiteNKPercent = Math.round((WhiteNK / svnthBlock.ordCunt) * 100)

        const BluePK = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'PK', 1);
        const BluePKPercent = Math.round((BluePK / egthBlock.ordCunt) * 100)

        const WhitePK = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'PK', 1);
        const WhitePKPercent = Math.round((WhitePK / egthBlock.ordCunt) * 100)

        const BlueFK = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'FK', 1);
        const BlueFKPercent = Math.round((BlueFK / nthBlock.ordCunt) * 100)

        const WhiteFK = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'FK', 1);
        const WhiteFKPercent = Math.round((WhiteFK / nthBlock.ordCunt) * 100)


        setColorOrderCount({
            Bnk: blackNK,
            Bnkp: blackNKPercent,
            Bpk: blackPK,
            Bpkp: blackPKPercent,
            Bfk: blackFK,
            Bfkp: blackFKPercent,
            Rnk: RedNK,
            Rnkp: RedNKPercent,
            Rpk: RedPK,
            Rpkp: RedPKPercent,
            Rfk: RedFK,
            Rfkp: RedFKPercent,
            Ynk: YellowNK,
            Ynkp: YellowNKPercent,
            Ypk: YellowPK,
            Ypkp: YellowPkPercent,
            Yfk: YellowFK,
            Yfkp: YellowFkPercent,
            Gnk: GreenNK,
            Gnkp: GreenNKPercent,
            Gpk: GreenPK,
            Gpkp: GreenPKPercent,
            Gfk: GreenFK,
            Gfkp: GreenFKPercent,
            Blnk: BlueNK,
            Blnkp: BlueNKPercent,
            Wnk: WhiteNK,
            Wnkp: WhiteNKPercent,
            Blpk: BluePK,
            Blpkp: BluePKPercent,
            Wpk: WhitePK,
            Wpkp: WhitePKPercent,
            Blfk: BlueFK,
            Blfkp: BlueFKPercent,
            Wfk: WhiteFK,
            Wfkp: WhiteFKPercent
        })

    }

    useEffect(() => {
        loadInitialData();
        setAnalyticalData();
    }, [SOData])

    const setAnalyticalData = () => {

        const blackCount: any = mapOrderDetails(SOData, ColorsMTO.Black.label, "", "", "", 0)
        const redCount: any = mapOrderDetails(SOData, ColorsMTO.Red.label, "", "", "", 0)
        const yellowCount: any = mapOrderDetails(SOData, ColorsMTO.Yellow.label, "", "", "", 0)
        const greenCount: any = mapOrderDetails(SOData, ColorsMTO.Green.label, "", "", "", 0)
        const blueCount: any = mapOrderDetails(SOData, ColorsMTO.Blue.label, ColorsMTO.White.label, "", "", 1);


        const TotalCountObj = {
            "Order": [
                { ...blackCount, color: ColorsMTO.Black.code },
                { ...redCount, color: ColorsMTO.Red.code },
                { ...yellowCount, color: ColorsMTO.Yellow.code },
                { ...greenCount, color: ColorsMTO.Green.code },
                { ...blueCount, color: ColorsMTO.Blue.code }
            ]
        }



        dispatch(SAVE_ANALYTICS_DATA(TotalCountObj))
    }

    const handleToggle = (c1: any, c2: any, c3: any, kit: string, S: string, E: string) => {

        setDetailDataObj({ c1, c2, c3, kit, S, E })
        // setToggleSubPage(true);
        handleToggleComponent(true);
    }

    function formatDate(start: any, end: any) {
        // if (start !== 0 || end !== 0) {
        return start + "-" + end + " Days";
        // }
    }

    return (
        <Main>
            {/**1st row */}
            <MainContainer>
                <Box
                    data-testid="btn_navigate"
                    onClick={() => handleToggle(ColorsMTO.Black.label, ColorsMTO.Red.label, ColorsMTO.Yellow.label, "NK", "0", "0")}>
                    <MTOMaterialSO
                        kit={"No Kit"}
                        colors={{ c1: ColorsMTO.Black.code, c2: ColorsMTO.Red.code, c3: ColorsMTO.Yellow.code }}
                        height={"18px"}
                        text={""}
                        orderCount={BRYNkOrdCunt}
                        cutCount={BRYNkCustCunt}
                        orderValue={BRYNkOrdVal}
                        percent={BRYNkOrdCunt / totalOrderCount}
                        ToolTipdata={{ 'c1': colorOrderCount?.Bnk, 'c2': colorOrderCount?.Rnk, 'c3': colorOrderCount?.Ynk, 'p3': colorOrderCount?.Ynkp, 'p1': colorOrderCount?.Bnkp, 'p2': colorOrderCount?.Rnkp }}
                    />
                </Box>
                <Box onClick={() => handleToggle(ColorsMTO.Black.label, ColorsMTO.Red.label, ColorsMTO.Yellow.label, "PK", "0", "0")}>
                    <MTOMaterialSO
                        kit={"Partial Kit"}
                        colors={{ c1: ColorsMTO.Black.code, c2: ColorsMTO.Red.code, c3: ColorsMTO.Yellow.code }}
                        height={"18px"}
                        text={""}
                        orderCount={secBlockOrdCnt}
                        cutCount={secBlockCustCnt}
                        orderValue={secOrderVal}
                        percent={secBlockOrdCnt / totalOrderCount}
                        ToolTipdata={{ 'c1': colorOrderCount?.Bpk, 'c2': colorOrderCount?.Rpk, 'c3': colorOrderCount?.Ypk, 'p1': colorOrderCount?.Bpkp, 'p2': colorOrderCount?.Rpkp, 'p3': colorOrderCount?.Ypkp }}
                    />
                </Box>
                <Box onClick={() => handleToggle(ColorsMTO.Black.label, ColorsMTO.Red.label, ColorsMTO.Yellow.label, "FK", "0", "0")}>
                    <MTOMaterialSO
                        kit={"Full  Kit"}
                        colors={{ c1: ColorsMTO.Black.code, c2: ColorsMTO.Red.code, c3: ColorsMTO.Yellow.code }}
                        height={"18px"}
                        text={""}
                        orderCount={thrdBlockOrdCnt}
                        cutCount={thrdBlockCustCnt}
                        orderValue={thrdOrderVal}
                        percent={thrdBlockOrdCnt / totalOrderCount}
                        ToolTipdata={{ 'c1': colorOrderCount?.Bfk, 'c2': colorOrderCount?.Rfk, 'c3': colorOrderCount?.Yfk, 'p1': colorOrderCount?.Bfkp, 'p2': colorOrderCount?.Rfkp, 'p3': colorOrderCount?.Yfkp, }}
                    />
                </Box>
            </MainContainer>



            <MainContainer>
                {/** 1st Box */}
                <Box onClick={() => handleToggle(ColorsMTO.Green.label, "", "", "NK", "0", "0")}>
                    <MTOMaterialSO
                        kit={"No Kit"}
                        colors={{ c1: ColorsMTO.Green.code, c2: null, c3: null }}
                        height={"36px"}
                        text={""}
                        orderCount={frthBlockOrdCnt}
                        cutCount={frthBlockCustCnt}
                        orderValue={frthOrderVal}
                        percent={frthBlockOrdCnt / totalOrderCount}
                        ToolTipdata={{ 'c1': colorOrderCount?.Gnk, 'p1': colorOrderCount?.Gnkp }}
                    />

                </Box>

                <Box onClick={() => handleToggle(ColorsMTO.Green.label, "", "", "PK", "0", "0")}>
                    <MTOMaterialSO
                        kit={"Partial Kit"}
                        colors={{ c1: ColorsMTO.Green.code, c2: null, c3: null }}
                        height={"36px"}
                        text={""}
                        orderCount={fifthBlockOrdCnt}
                        cutCount={fifthBlockCustCnt}
                        orderValue={fifthOrderVal}
                        percent={fifthBlockOrdCnt / totalOrderCount}
                        ToolTipdata={{ 'c1': colorOrderCount?.Gpk, 'p1': colorOrderCount?.Gpkp }}
                    />

                </Box>

                <Box onClick={() => handleToggle(ColorsMTO.Green.label, "", "", "FK", "0", "0")}>
                    <MTOMaterialSO
                        kit={"Full Kit"}
                        colors={{ c1: ColorsMTO.Green.code, c2: null, c3: null }}
                        height={"36px"}
                        text={""}
                        orderCount={sxthBlockOrdCnt}
                        cutCount={sxthBlockCustCnt}
                        orderValue={sxthdOrderVal}
                        percent={sxthBlockOrdCnt / totalOrderCount}
                        ToolTipdata={{ 'c1': colorOrderCount?.Gfk, 'p1': colorOrderCount?.Gfkp }}
                    />

                </Box>
            </MainContainer>


            <div style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'center',
                paddingLeft: '20px'
            }}>

                <div style={{
                    width: "98%",

                    border: `1px dashed ${ColorsMTO.LightGrey.code}`,
                    color: ColorsMTO.White.code,
                    marginBottom: '20px'
                }}>
                </div>
            </div>

            <MainContainer >
                <Box onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "NK", svthSrtDt, svthEndDt)}>
                    <MTOMaterialSO
                        kit={"No Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={formatDate(svthSrtDt, svthEndDt)}
                        orderCount={svthBlockOrdCnt}
                        cutCount={svthBlockCustCnt}
                        orderValue={svthdOrderVal}
                        percent={svthBlockOrdCnt / totalBlueOrdCount}
                        ToolTipdata={{ 'c3': colorOrderCount?.Blnk, 'c2': colorOrderCount?.Wnk, 'p3': colorOrderCount?.Blnkp, 'p2': colorOrderCount?.Wnkp }}
                    />

                </Box>
                <Box onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "PK", egthSrtDt, egthEndDt)}>
                    <MTOMaterialSO
                        kit={"Partial Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={formatDate(egthSrtDt, egthEndDt)}
                        orderCount={egthBlockOrdCnt}
                        cutCount={egthBlockCustCnt}
                        orderValue={egthdOrderVal}
                        percent={egthBlockOrdCnt / totalBlueOrdCount} 
                        ToolTipdata={{ 'c3': colorOrderCount?.Blpk, 'c2': colorOrderCount?.Wpk, 'p3': colorOrderCount?.Blpkp, 'p2': colorOrderCount?.Wpkp }}
                    />

                </Box>
                <Box onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "FK", nthSrtDt, nthEndDt)}>
                    <MTOMaterialSO
                        kit={"Full Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={formatDate(nthSrtDt, nthEndDt)}
                        orderCount={nthBlockOrdCnt}
                        cutCount={nthBlockCustCnt}
                        orderValue={nthhdOrderVal}
                        percent={nthBlockOrdCnt / totalBlueOrdCount}
                        ToolTipdata={{ 'c2': colorOrderCount?.Wfk, 'c3': colorOrderCount?.Blfk, 'p2': colorOrderCount?.Wfkp, 'p3': colorOrderCount?.Blfkp }}
                    />

                </Box>
            </MainContainer>

        </Main>
    )
}

export default CurrentCov