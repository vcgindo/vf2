/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'

export namespace ManualUploadService {
  export const uploadFile = async (formData: any) => {
    return await axios.post('/api/manual-upload/import-csv/', formData)
  }
}
