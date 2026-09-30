import React from 'react'
import ApplicationSelectModal from './ApplicationSelectModal'

const MastersInterceptor = ({url}: any) => {
  return (
    <ApplicationSelectModal redirectUrl={url}/>
  )
}

export default MastersInterceptor