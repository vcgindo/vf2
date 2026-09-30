import _ from 'lodash';
import React from 'react'
import { useDispatch, useSelector } from 'react-redux';
import { SET_POOGI_MODIFY_DATA } from '../../../../../redux/actions/MTO';
import { UPDATE_ROW_DATA } from '../../../../../redux/actions/MDM';
import { RootState } from '../../../../../redux/store/store';

const MajReasonDescCell = (props:any) => {
    const activeMaster = useSelector((state:RootState) => state.mdm.activeMaster);

    const initialPoogiData = useSelector((state: any)=> state.mto.poogiIntialData);
    const poogiModifyData = useSelector((state:any)=> state.mto.poogiModifyData);

    const dispatch = useDispatch();

    const undo = ()=>{
        if(!props.data.id){


            const newData = _.cloneDeep(activeMaster.rowData);
            newData.forEach((ele: any)=>{
                if(ele.majId===props.data.majId){
                    initialPoogiData.forEach((elm:any)=>{
                        if(elm.majId===ele.majId){
                            ele.majdsc = elm.majdsc;
                            ele.iu = false;
                        }
                    })
                }
            })
            dispatch(UPDATE_ROW_DATA(newData));

            const newModifyData= _.cloneDeep(poogiModifyData);
            newModifyData.forEach((elm:any)=>{
                if(elm.majId===props.data.majId){
                    initialPoogiData.forEach((el:any)=>{
                        if(el.majId===props.data.majId){
                            elm.majdsc = el.majdsc;
                            elm.iu = false;
                        }
                    })
                }
            })

            dispatch(SET_POOGI_MODIFY_DATA(newModifyData));


        }
    }
  return (
    <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '4px', opacity: `${props.data.id?0.3:1}`}}>
        <span>{props.data.majdsc}</span>
        {(props.data.iu && !props.data.in) &&<span style={{paddingTop: '2px', cursor: 'pointer'}}>
            <img  onClick={undo} height={18} width={18} src="/assets/img/undo.svg" alt="undo" />
        </span>}
    </div>
  )
}

export default MajReasonDescCell