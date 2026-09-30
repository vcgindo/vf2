/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios'

export namespace PendingISTRequestsService {
  export const getList = async () => {
    return await axios.get('/')
  }
}
