import { CSSProperties } from "react"
import { GridHealthType,TableLabelProps,TableLabelStatus } from "../../../../../types/MCGrid"
import Store from "./Store"
import StoreGroup from "./StoreGroup"
import {ViewBottombar, ViewContainer, ViewGridWrapper, ViewSidebar, ViewTableLabelCell, ViewTableLabelCellWrapper, ViewTopbar, ViewWrapper } from "./styles"



const TableLabel = (props:TableLabelProps)=>{

    const getStyles = (status:TableLabelStatus):CSSProperties=>{
        switch(status){
            case "surplus":
                return {
                    color:'#585757',
                    backgroundColor:'#EBE5E5'
                }
            case "complete":
                return {
                    color:'#306A0F',
                    backgroundColor:'#AEE293'
                }
            case "incomplete":
                return {
                    color:'#816F08',
                    backgroundColor:'#F5E58A'
                }
            case "very-incomplete":
                return {
                    color:'#C61C1C',
                    backgroundColor:'#FFD0D0'
                }
            case "high":
                return {
                    color:'#306A0F',
                    backgroundColor:'#AEE293'
                }
            case "medium":
                return {
                    color:'#816F08',
                    backgroundColor:'#F5E58A'
                }
            case "low":
                return {
                    color:'#C61C1C',
                    backgroundColor:'#FFD0D0'
                }
            default:
                return {
                    color:'#585757',
                    backgroundColor:'#EBE5E5'
                }
        }
    }

    return(
        <ViewTableLabelCellWrapper>
            <ViewTableLabelCell style={{...getStyles(props.status)}}>
                {props.text}
            </ViewTableLabelCell>
        </ViewTableLabelCellWrapper>
    )
}

const ChartView  = (props:{data:GridHealthType})=>{
    const {
        data
    } = props

    return(
        <ViewWrapper>
            <ViewContainer>
                <ViewTopbar>
                    <h1>Health of Grid</h1>
                </ViewTopbar>
                <ViewSidebar>
                    <TableLabel status="surplus" text="Surplus"/>
                    <TableLabel status="complete" text="Complete"/>
                    <TableLabel status="incomplete" text="Incomplete"/>
                    <TableLabel status="very-incomplete" text="Very Incomplete"/>
                </ViewSidebar>
                <ViewBottombar>
                    <TableLabel status="low" text="Low ITR"/>
                    <TableLabel status="medium" text="Medium ITR"/>
                    <TableLabel status="high" text="High ITR"/>
                </ViewBottombar>
                <ViewGridWrapper>
                        <Store data={data.surplus.low} type="floating" status="surplus"/>
                        <Store data={data.surplus.medium} type="floating" status="surplus"/>
                        <Store data={data.surplus.high} type="default" status="surplus"/>

                        <Store data={data.complete.low} type="default" status="complete"/>

                        <Store data={data.complete.medium} type="default" status="complete"/>
                        <Store data={data.complete.high} type="default" status="complete"/>

                        <StoreGroup data={data.incomplete.low}  status="incomplete"/>
                        <StoreGroup data={data.incomplete.medium}  status="incomplete"/>
                        <StoreGroup data={data.incomplete.high}  status="incomplete"/>
                        <StoreGroup data={data["very-incomplete"].low}  status="very-incomplete"/>
                        <StoreGroup data={data["very-incomplete"].medium}  status="very-incomplete"/>
                        <StoreGroup data={data["very-incomplete"].high}  status="very-incomplete"/>
                </ViewGridWrapper>
            </ViewContainer>
        </ViewWrapper>
    )
}

export default ChartView