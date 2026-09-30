
import axios from 'axios';

  export const getLoginAuditReportData = async () => {
    return await axios.get(
      process.env.REACT_APP_API_HOST + `api/user/login-audit-report/`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  }
