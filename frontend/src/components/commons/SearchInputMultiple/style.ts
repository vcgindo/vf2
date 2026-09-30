import * as globalStyles from '../../../styles/global'

export const selectStyles =(backgroundColor:string,borderRadius:number, boxShadow:string,themeUi:string)=> {
  return{
  control: (provided: any, state: any) => ({
    ...provided,
    minWidth: 223,
    margin: 8,
    background: backgroundColor,
    fontSize: 16,
    outline: 'none',
    borderRadius: borderRadius ? borderRadius : 6,
    cursor: 'pointer',
    border: '1px solid rgb(204, 204, 204)',
    // This line disable the blue border
     boxShadow: state.isFocused ? 0 : boxShadow ?  boxShadow : '0px 6px 12px #95959529' ,
      paddingRight: '13px',
    }),
  multiValue: () => ({
    display: 'flex',
    backgroundColor: '#313131',
    color: `${globalStyles.white}`,
    margin: '5px',
    padding: '7px',
    borderRadius: '20px',

  }),
  multiValueLabel: (provided: any) => ({
    ...provided,
    color:`${globalStyles.white}` , 
    font: 'normal normal 300 13px/ 13px Roboto',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    padding: '3px 5px 3px 6px',
    
  }),
  multiValueRemove: () => ({
    display: 'flex',
    margin: 'auto',
    colors: 'red',
    borderRadius: '50%',
    border: '1px solid',
    cursor: 'pointer'
  }),
  clearIndicator: () => ({
    display: 'none'
  }),
  option: (provided: any, {isFocused, isSelected}: any) =>  { 
    return (
    {
    ...provided,
        cursor: 'pointer',

        backgroundColor: isSelected ? themeUi==="REGALBLAZE"?"#FCA311":"#BC3D81": "white",
        // cursor: 'pointer',
        "&:hover": {
          backgroundColor: themeUi==="REGALBLAZE"?"rgb(252, 163, 17,0.3)":'#bc3d814d',
          color:"black",
      },
      // backgroundColor: isSelected ? "pink" : "blue",
        // color: isFocused ? 'black' : 'black',
      color:isSelected?'white':'black'
  })},
  menuList: (provided: any) => ({
    ...provided,
    cursor: 'pointer',
    maxHeight: '160px',
    zIndex: 3,
    width: '100%',
    background: `${globalStyles.white}`,
    position: 'absolute',
    boxShadow: '0px 10px 20px #C4C8D066',
    '::-webkit-scrollbar': {
      width: '7px',
      height: '0px'
    },
    '::-webkit-scrollbar-track': {
      background: '#F2F2F2 0% 0% no-repeat padding-box'
    },
    '::-webkit-scrollbar-thumb': {
      background: '#313131 0% 0% no-repeat padding-box',
      borderRadius: '30px'
    }
  }),
  menu: () => ({
    boxShadow: 'inset 0 1px 0 rgba(0, 0, 0, 0.1)',
    width: '98%',
    fontSize: 14
  }),
  dropdownIndicator: (provided: any) => ({
    ...provided,
    display: 'none' // Ẩn mũi tên
  }), 
  placeholder:()=>({
    paddingLeft:'15px',
  }),
  valueContainer:()=>({
    overflow:'auto',
    maxHeight:'40px',
    width:'90%', 
    display:'flex',
    alignItems:'center',
    '&::-webkit-scrollbar': {
      width: '7px',
       display:'none',
      
    },
    '&::-webkit-scrollbar-track': {
      borderRadius: '30px',
      opacity: 1,
    },
    '&::-webkit-scrollbar-thumb': {
      width: '7px',
      background: '#D1D1D1 0% 0% no-repeat padding-box',
      boxShadow: '0px 6px 9px #F8F8F8',
      borderRadius: '30px',
      opacity: 1,
    },
    }),
  
}
}


export const styleMoreSelect = {
  display: 'flex',
  backgroundColor: '#313131',
  color: '#fff',
  margin: '5px',
  padding: '7px 10px 0 10px',
  fontSize: '13px',
  borderRadius: '20px',
  height: '33px',
  fontWeight: 300
}
