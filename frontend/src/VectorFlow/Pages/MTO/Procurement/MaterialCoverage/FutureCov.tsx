import { useState, useEffect } from 'react';
import { ColorsMTO } from '../../Common/Colors';
import {
    MainContainer,
    Box,
    Main,
} from '../MaterialCoverage/styles';
import MTOMaterialSO from '../../../../../components/VectorFLOW/commons/MTO/MaterialSOBox/MTOMaterialSO';
import { mapOrderDetails, calculatePercentage, DetailsObj, calculateColorOrderCount } from './CommonFunc';

interface FutureCovProps {
    data: any,
    handleToggleComponent: any,
    setDetailDataObj: (data: DetailsObj) => void
}

interface useRedStateProps {
    bnk1: number,
    wnk1: number,
    bnkp1: number,
    wnkp1: number,

    bpk1: number,
    wpk1: number,
    bpkp1: number,
    wpkp1: number,

    bfk1: number,
    wfk1: number,
    bfkp1: number,
    wfkp1: number,


    bnk2: number,
    wnk2: number,
    bnkp2: number,
    wnkp2: number,

    bpk2: number,
    wpk2: number,
    bpkp2: number,
    wpkp2: number,

    bfk2: number,
    wfk2: number,
    bfkp2: number,
    wfkp2: number,


    bnk3: number,
    wnk3: number,
    bnkp3: number,
    wnkp3: number,

    bpk3: number,
    wpk3: number,
    bpkp3: number,
    wpkp3: number,

    bfk3: number,
    wfk3: number,
    bfkp3: number,
    wfkp3: number,

}

const FutureCov = ({ data: SOData, handleToggleComponent, setDetailDataObj }: FutureCovProps) => {
    // const [SOData, setSOData] = useState<string[]>(SOData);
    const [totalOrderCount2, setTotalOrdeerCount2] = useState<number>(0);
    const [totalOrderCount3, setTotalOrdeerCount3] = useState<number>(0);
    const [totalOrderCount4, setTotalOrdeerCount4] = useState<number>(0);

    const [colorOrderCount, setColorOrderCount] = useState<useRedStateProps>()
    // const [isSubPageOpen, setToggleSubPage] = useState<boolean>(false)


    const [BRYNkOrdCunt, setBRYNkOrdCunt] = useState<number>(0);
    const [BRYNkCustCunt, setBRYNkCustCunt] = useState<number>(0);
    const [BRYNkOrdVal, setBRYNkOrderVal] = useState<number>(0);
    const [BRYSrtDt, setBRYSrtDt] = useState<string>('');
    const [BRYEndDt, setBRYEndDt] = useState<string>('');

    const [secBlockOrdCnt, setSecBlockOrdCnt] = useState<number>(0);
    const [secBlockCustCnt, setSecBlockCustCnt] = useState<number>(0);
    const [secOrderVal, setsecOrderVal] = useState<number>(0);
    const [secSrtDt, setSecSrtDt] = useState<string>('');
    const [secEndDt, setsecEndDt] = useState<string>('');

    const [thrdBlockOrdCnt, setthrdBlockOrdCnt] = useState<number>(0);
    const [thrdBlockCustCnt, setthrdBlockCustCnt] = useState<number>(0);
    const [thrdOrderVal, setthrdOrderVal] = useState<number>(0);
    const [thrdSrtDt, setthrdSrtDt] = useState<string>('');
    const [thrdEndDt, setthrdEndDt] = useState<string>('');

    const [frthBlockOrdCnt, setfrthBlockOrdCnt] = useState<number>(0);
    const [frthBlockCustCnt, setfrthBlockCustCnt] = useState<number>(0);
    const [frthOrderVal, setfrthdOrderVal] = useState<number>(0);
    const [frthSrtDt, setfrthSrtDt] = useState<string>('');
    const [frthEndDt, setfrthEndDt] = useState<string>('');

    const [fifthBlockOrdCnt, setfifthBlockOrdCnt] = useState<number>(0);
    const [fifthBlockCustCnt, setfifthBlockCustCnt] = useState<number>(0);
    const [fifthOrderVal, setfifthdOrderVal] = useState<number>(0);
    const [fifthSrtDt, setfifthSrtDt] = useState<string>('');
    const [fifthEndDt, setfifthEndDt] = useState<string>('');

    const [sxthBlockCustCnt, setsxthBlockCustCnt] = useState<number>(0);
    const [sxthBlockOrdCnt, setsxthBlockOrdCnt] = useState<number>(0);
    const [sxthdOrderVal, setsxthdOrderVal] = useState<number>(0);
    const [sxthSrtDt, setsxthSrtDt] = useState<string>('');
    const [sxthEndDt, setsxthEndDt] = useState<string>('');

    const [svthBlockCustCnt, setsvthBlockCustCnt] = useState<number>(0);
    const [svthBlockOrdCnt, setsvthBlockOrdCnt] = useState<number>(0);
    const [svthdOrderVal, setsvthdOrderVal] = useState<number>(0);
    const [svthSrtDt, setsvthSrtDt] = useState<string>('');
    const [svthEndDt, setsvthEndDt] = useState<string>('');

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
        const totalOrdCOunt2: any = calculatePercentage(SOData, "Blue", "White", "", "", 2);
        setTotalOrdeerCount2(totalOrdCOunt2);
        const totalOrdCOunt3: any = calculatePercentage(SOData, "Blue", "White", "", "", 3);
        setTotalOrdeerCount3(totalOrdCOunt3);
        const totalOrdCOunt4: any = calculatePercentage(SOData, "Blue", "White", "", "", 4);
        setTotalOrdeerCount4(totalOrdCOunt4);

        const firstBlock: any = mapOrderDetails(SOData, "Blue", "White", "", "NK", 2);

        setBRYNkCustCunt(firstBlock.cusCunt);
        setBRYNkOrdCunt(firstBlock.ordCunt);
        setBRYNkOrderVal(firstBlock.totalCunt);
        setBRYSrtDt(firstBlock.stdt);
        setBRYEndDt(firstBlock.endt);

        const secondBlock: any = mapOrderDetails(SOData, "Blue", "White", "", "PK", 2);
        setSecBlockCustCnt(secondBlock.cusCunt);
        setSecBlockOrdCnt(secondBlock.ordCunt);
        setsecOrderVal(secondBlock.totalCunt);
        setSecSrtDt(secondBlock.stdt);
        setsecEndDt(secondBlock.endt);

        const thirdBlock: any = mapOrderDetails(SOData, "Blue", "White", "", "FK", 2);
        setthrdBlockCustCnt(thirdBlock.cusCunt);
        setthrdBlockOrdCnt(thirdBlock.ordCunt);
        setthrdOrderVal(thirdBlock.totalCunt);
        setthrdSrtDt(thirdBlock.stdt);
        setthrdEndDt(thirdBlock.endt);

        const frthBlock: any = mapOrderDetails(SOData, "Blue", "White", "", "NK", 3);
        setfrthBlockCustCnt(frthBlock.cusCunt);
        setfrthBlockOrdCnt(frthBlock.ordCunt);
        setfrthdOrderVal(frthBlock.totalCunt);
        setfrthSrtDt(frthBlock.stdt);
        setfrthEndDt(frthBlock.endt);

        const fifthBlock: any = mapOrderDetails(SOData, "Blue", "White", "", "PK", 3);
        setfifthBlockCustCnt(fifthBlock.cusCunt);
        setfifthBlockOrdCnt(fifthBlock.ordCunt);
        setfifthdOrderVal(fifthBlock.totalCunt);
        setfifthSrtDt(fifthBlock.stdt);
        setfifthEndDt(fifthBlock.endt);

        const sxthBlock: any = mapOrderDetails(SOData, "Blue", "White", "", "FK", 3);
        setsxthBlockCustCnt(sxthBlock.cusCunt);
        setsxthBlockOrdCnt(sxthBlock.ordCunt);
        setsxthdOrderVal(sxthBlock.totalCunt);
        setsxthSrtDt(sxthBlock.stdt);
        setsxthEndDt(sxthBlock.endt);

        const svnthBlock: any = mapOrderDetails(SOData, "Blue", "White", "", "NK", 4);
        setsvthBlockCustCnt(svnthBlock.cusCunt);
        setsvthBlockOrdCnt(svnthBlock.ordCunt);
        setsvthdOrderVal(svnthBlock.totalCunt);
        setsvthSrtDt(svnthBlock.stdt);
        setsvthEndDt(svnthBlock.endt);

        const egthBlock: any = mapOrderDetails(SOData, "Blue", "White", "", "PK", 4);
        setegthBlockCustCnt(egthBlock.cusCunt);
        setegthBlockOrdCnt(egthBlock.ordCunt);
        setegthdOrderVal(egthBlock.totalCunt);
        setegthSrtDt(egthBlock.stdt);
        setegthEndDt(egthBlock.endt);

        const nthBlock: any = mapOrderDetails(SOData, "Blue", "White", "", "FK", 4);
        setnthBlockCustCnt(nthBlock.cusCunt);
        setnthBlockOrdCnt(nthBlock.ordCunt);
        setnthhdOrderVal(nthBlock.totalCunt);
        setnthSrtDt(nthBlock.stdt);
        setnthEndDt(nthBlock.endt);


        const blueNK_2 = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'NK', 2)
        const whiteNK_2 = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'NK', 2);
        const blueNK_2_Percent = Math.round((blueNK_2 / firstBlock.ordCunt) * 100)
        const whiteNK_2_Percent = Math.round((whiteNK_2 / firstBlock.ordCunt) * 100)

        const bluePK_2 = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'PK', 2);
        const whitePK_2 = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'PK', 2);
        const bluePK_2_Percent = Math.round((bluePK_2 / secondBlock.ordCunt) * 100)
        const whitePK_2_Percent = Math.round((whitePK_2 / secondBlock.ordCunt) * 100)

        const blueFK_2 = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'FK', 2);
        const whiteFK_2 = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'FK', 2);
        const blueFK_2_Percent = Math.round((blueFK_2 / thirdBlock.ordCunt) * 100)
        const whiteFK_2_Percent = Math.round((whiteFK_2 / thirdBlock.ordCunt) * 100)

        const blueNK_3 = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'NK', 3);
        const whiteNK_3 = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'NK', 3);
        const blueNK_3_Percent = Math.round((blueNK_3 / frthBlock.ordCunt) * 100)
        const whiteNK_3_Percent = Math.round((whiteNK_3 / frthBlock.ordCunt) * 100)

        const bluePK_3 = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'PK', 3);
        const whitePK_3 = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'PK', 3);
        const bluePK_3_Percent = Math.round((bluePK_3 / fifthBlock.ordCunt) * 100)
        const whitePK_3_Percent = Math.round((whitePK_3 / fifthBlock.ordCunt) * 100)

        const blueFK_3 = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'FK', 3);
        const whiteFK_3 = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'FK', 3);
        const blueFK_3_Percent = Math.round((blueFK_3 / sxthBlock.ordCunt) * 100)
        const whiteFK_3_Percent = Math.round((whiteFK_3 / sxthBlock.ordCunt) * 100)

        const blueNK_4 = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'NK', 4);
        const whiteNK_4 = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'NK', 4);
        const blueNK_4_Percent = Math.round((blueNK_4 / svnthBlock.ordCunt) * 100)
        const whiteNK_4_Percent = Math.round((whiteNK_4 / svnthBlock.ordCunt) * 100)

        const bluePK_4 = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'PK', 4);
        const whitePK_4 = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'PK', 4);
        const bluePK_4_Percent = Math.round((bluePK_4 / egthBlock.ordCunt) * 100)
        const whitePK_4_Percent = Math.round((whitePK_4 / egthBlock.ordCunt) * 100)

        const blueFK_4 = calculateColorOrderCount(SOData, ColorsMTO.Blue.label, 'FK', 4);
        const whiteFK_4 = calculateColorOrderCount(SOData, ColorsMTO.White.label, 'FK', 4);
        const blueFK_4_Percent = Math.round((blueFK_4 / nthBlock.ordCunt) * 100)
        const whiteFK_4_Percent = Math.round((whiteFK_4 / nthBlock.ordCunt) * 100)


        setColorOrderCount({
            bnk1: blueNK_2,
            wnk1: whiteNK_2,
            bnkp1: blueNK_2_Percent,
            wnkp1: whiteNK_2_Percent,

            bpk1: bluePK_2,
            wpk1: whitePK_2,
            bpkp1: bluePK_2_Percent,
            wpkp1: whitePK_2_Percent,

            bfk1: blueFK_2,
            wfk1: whiteFK_2,
            bfkp1: blueFK_2_Percent,
            wfkp1: whiteFK_2_Percent,


            bnk2: blueNK_3,
            wnk2: whiteNK_3,
            bnkp2: blueNK_3_Percent,
            wnkp2: whiteNK_3_Percent,

            bpk2: bluePK_3,
            wpk2: whitePK_3,
            bpkp2: bluePK_3_Percent,
            wpkp2: whitePK_3_Percent,

            bfk2: blueFK_3,
            wfk2: whiteFK_3,
            bfkp2: blueFK_3_Percent,
            wfkp2: whiteFK_3_Percent,


            bnk3: blueNK_4,
            wnk3: whiteNK_4,
            bnkp3: blueNK_4_Percent,
            wnkp3: whiteNK_4_Percent,

            bpk3: bluePK_4,
            wpk3: whitePK_4,
            bpkp3: bluePK_4_Percent,
            wpkp3: whitePK_4_Percent,

            bfk3: blueFK_4,
            wfk3: whiteFK_4,
            bfkp3: blueFK_4_Percent,
            wfkp3: whiteFK_4_Percent,
        })


    }

    useEffect(() => {
        loadInitialData();
    }, [SOData])

    const handleToggle = (c1: any, c2: any, c3: any, kit: string, S: string, E: string) => {
        setDetailDataObj({ c1, c2, c3, kit, S, E })
        // setToggleSubPage(true);
        handleToggleComponent(true);
    }

    return (
        <Main>
            {/**1st row */}

            <MainContainer>
                <Box
                    data-testid="btn_navigate"
                    onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "NK", BRYSrtDt, BRYEndDt)}>
                    <MTOMaterialSO
                        kit={"No Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={BRYSrtDt + "-" + BRYEndDt + " Days"}
                        orderCount={BRYNkOrdCunt}
                        cutCount={BRYNkCustCunt}
                        orderValue={BRYNkOrdVal}
                        percent={BRYNkOrdCunt / totalOrderCount2}
                        ToolTipdata={{ 'c2': colorOrderCount?.wnk1, 'c3': colorOrderCount?.bnk1, 'p2': colorOrderCount?.wnkp1, 'p3': colorOrderCount?.bnkp1 }}
                    />
                </Box>
                <Box
                    data-testid="handleNavigation"
                    onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "PK", secSrtDt, secEndDt)}>
                    <MTOMaterialSO
                        kit={"Partial Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={secSrtDt + "-" + secEndDt + " Days"}
                        orderCount={secBlockOrdCnt}
                        cutCount={secBlockCustCnt}
                        orderValue={secOrderVal}
                        percent={secBlockOrdCnt / totalOrderCount2}
                        ToolTipdata={{ 'c2': colorOrderCount?.wpk1, 'c3': colorOrderCount?.bpk1, 'p2': colorOrderCount?.wpkp1, 'p3': colorOrderCount?.bpkp1 }}
                    />
                </Box>
                <Box
                    data-testid="handleNavigation"
                    onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "FK", thrdSrtDt, thrdEndDt)}>
                    <MTOMaterialSO
                        kit={"Full Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={thrdSrtDt + "-" + thrdEndDt + " Days"}
                        orderCount={thrdBlockOrdCnt}
                        cutCount={thrdBlockCustCnt}
                        orderValue={thrdOrderVal}
                        percent={thrdBlockOrdCnt / totalOrderCount2}
                        ToolTipdata={{ 'c2': colorOrderCount?.wfk1, 'c3': colorOrderCount?.bfk1, 'p2': colorOrderCount?.wfkp1, 'p3': colorOrderCount?.bfkp1 }}
                    />
                </Box>
            </MainContainer>



            <MainContainer>
                <Box
                    data-testid="handleNavigation"
                    onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "NK", frthSrtDt, frthEndDt)}>
                    <MTOMaterialSO
                        kit={"No Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={frthSrtDt + "-" + frthEndDt + " Days"}
                        orderCount={frthBlockOrdCnt}
                        cutCount={frthBlockCustCnt}
                        orderValue={frthOrderVal}
                        percent={frthBlockOrdCnt / totalOrderCount3}
                        ToolTipdata={{ 'c2': colorOrderCount?.wnk2, 'c3': colorOrderCount?.bnk2, 'p2': colorOrderCount?.wnkp2, 'p3': colorOrderCount?.bnkp2 }}
                    />

                </Box>

                <Box
                    data-testid="handleNavigation"
                    onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "PK", fifthSrtDt, fifthEndDt)}>
                    <MTOMaterialSO
                        kit={"Partial Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={fifthSrtDt + "-" + fifthEndDt + " Days"}
                        orderCount={fifthBlockOrdCnt}
                        cutCount={fifthBlockCustCnt}
                        orderValue={fifthOrderVal}
                        percent={fifthBlockOrdCnt / totalOrderCount3}
                        ToolTipdata={{ 'c2': colorOrderCount?.wpk2, 'c3': colorOrderCount?.bpk2, 'p2': colorOrderCount?.wpkp2, 'p3': colorOrderCount?.bpkp2 }}
                    />

                </Box>

                <Box
                    data-testid="handleNavigation"
                    onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "FK", sxthSrtDt, sxthEndDt)}>
                    <MTOMaterialSO
                        kit={"Full Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={sxthSrtDt + "-" + sxthEndDt + " Days"}
                        orderCount={sxthBlockOrdCnt}
                        cutCount={sxthBlockCustCnt}
                        orderValue={sxthdOrderVal}
                        percent={sxthBlockOrdCnt / totalOrderCount3}
                        ToolTipdata={{ 'c2': colorOrderCount?.wfk2, 'c3': colorOrderCount?.bfk2, 'p2': colorOrderCount?.wfkp2, 'p3': colorOrderCount?.bfkp2 }}
                    />

                </Box>
            </MainContainer>

            <MainContainer>
                <Box
                    data-testid="handleNavigation"
                    onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "NK", svthSrtDt, svthEndDt)}>
                    <MTOMaterialSO
                        kit={"No Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={svthSrtDt + "-" + svthEndDt + " Days"}
                        orderCount={svthBlockOrdCnt}
                        cutCount={svthBlockCustCnt}
                        orderValue={svthdOrderVal}
                        percent={svthBlockOrdCnt / totalOrderCount4}
                        ToolTipdata={{ 'c2': colorOrderCount?.wnk3, 'c3': colorOrderCount?.bnk3, 'p2': colorOrderCount?.wnkp3, 'p3': colorOrderCount?.bnkp3 }}
                    />

                </Box>
                <Box
                    data-testid="handleNavigation"
                    onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "PK", egthSrtDt, egthEndDt)}>
                    <MTOMaterialSO
                        kit={"Partial Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={egthSrtDt + "-" + egthEndDt + " Days"}
                        orderCount={egthBlockOrdCnt}
                        cutCount={egthBlockCustCnt}
                        orderValue={egthdOrderVal}
                        percent={egthBlockOrdCnt / totalOrderCount4}
                        ToolTipdata={{ 'c2': colorOrderCount?.wpk3, 'c3': colorOrderCount?.bpk3, 'p2': colorOrderCount?.wpkp3, 'p3': colorOrderCount?.bpkp3 }}
                    />

                </Box>
                <Box
                    data-testid="handleNavigation"
                    onClick={() => handleToggle(ColorsMTO.Blue.label, ColorsMTO.White.label, "", "FK", nthSrtDt, nthEndDt)}>
                    <MTOMaterialSO
                        kit={"Full Kit"}
                        colors={{ c1: ColorsMTO.Blue.code, c2: null, c3: null }}
                        height={"72px"}
                        text={nthSrtDt + "-" + nthEndDt + " Days"}
                        orderCount={nthBlockOrdCnt}
                        cutCount={nthBlockCustCnt}
                        orderValue={nthhdOrderVal}
                        percent={nthBlockOrdCnt / totalOrderCount4}
                        ToolTipdata={{ 'c2': colorOrderCount?.wfk3, 'c3': colorOrderCount?.bfk3, 'p2': colorOrderCount?.wfkp3, 'p3': colorOrderCount?.bfkp3 }}
                    />

                </Box>

            </MainContainer>

        </Main>
    )
}

export default FutureCov