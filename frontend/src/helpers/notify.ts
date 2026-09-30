import { toast, ToastOptions, type Theme, type ToastPosition } from 'react-toastify'

interface PromiseToastMsg{
  pending:string
  success:string
  error:string
}


export const ATTR_TOAST = {
  position: 'top-right',
  autoClose: 4000,
  hideProgressBar: false,
  closeOnClick: true,
  pauseOnHover: true,
  theme: 'colored'
} as {
  position: ToastPosition
  autoClose: number
  hideProgressBar: boolean
  closeOnClick: boolean
  pauseOnHover: boolean
  theme?: Theme
}

export const notifyError = (msg: string) =>{
  toast.dismiss()
  return toast.error(msg, ATTR_TOAST)
}


export const ATTR_TOAST_WITHOUT_AUTOCLOSE: ToastOptions = {
  position: 'top-right',
  autoClose: false,
  hideProgressBar: true,
  theme: 'colored'
}

export const notifyErrorWithoutAutoClose = (msg: any) =>{
  toast.dismiss()
  return toast.error(msg, ATTR_TOAST_WITHOUT_AUTOCLOSE)
}

export const notifySuccess = (msg: string) =>{
  toast.dismiss()
  return toast.success(msg, ATTR_TOAST)
}

export const notifyPromise = (promise:Promise<unknown>,msgs:PromiseToastMsg)=>{
  toast.dismiss()
  return toast.promise(promise,msgs,ATTR_TOAST)
}

export const notifyLoader = (msg: string) =>{
  toast.dismiss()
  return toast.loading(msg)
}

export const notifyWarning = (msg: string) =>{
  toast.dismiss()
  return toast.warning(msg, ATTR_TOAST)
}

export const notifyWarningWithoutAutoClose = (msg: string) => {
  return toast.warning(msg, {
    ...ATTR_TOAST,
    autoClose: false, 
  })
}
