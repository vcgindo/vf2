import { useEffect, useRef, useState } from "react";
import { UploadSectionWrapper } from "./style";
import UploadRightSection from "./UploadRightSection";
import UploadLeftSection from "./UploadLeftSection";
import NoDataToDisplay from "./NoDataToDisplay";
import { notifyError } from "../../../helpers/notify";
import { usePostUsersDataForValidations } from "../../../services/profile";
import readXlsxFile, { readSheetNames } from "read-excel-file";

function UploadWrapperSection({
  setIsAssignPageOpen,
  setValidUserData,
  validUserData,
}: any) {
  const [noData, setNoData] = useState(true);
  const [errorCount, setErrorCount] = useState(0);
  const [errorData, setErrorData] = useState<any>([]);
  const [progress, setProgress] = useState(0);

  const REQUIRED_HEADERS = ["Username", "Email ID", "Password"];
  const MAX_RECORDS = 100;

  const {
    mutateAsync: postUsersDataForValidation,
    isLoading,
    isSuccess,
  } = usePostUsersDataForValidations();

  const [file, setFile] = useState<any>();

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number | null>(null); // Track when loading started

  useEffect(() => {
    if (isLoading) {
      // Clear previous interval
      if (intervalRef.current) clearInterval(intervalRef.current);

      // Start from 0
      setProgress(0);
      let current = 0;
      startTimeRef.current = Date.now();

      intervalRef.current = setInterval(() => {
        current += 1;
        if (current <= 90) {
          setProgress(current);
        } else {
          clearInterval(intervalRef.current!);
        }
      }, 500); // Speed of progress increase
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isLoading]);

  useEffect(() => {
    if (isSuccess) {
      const now = Date.now();
      const minDuration = 4000; // ms (your debounce time)
      const elapsed = startTimeRef.current ? now - startTimeRef.current : 0;
      const delay = Math.max(minDuration - elapsed, 0);

      // Ensure progress continues at least for `minDuration` before jumping to 100%
      const timeout = setTimeout(() => {
        setProgress(100);
        if (intervalRef.current) clearInterval(intervalRef.current);
      }, delay);

      return () => clearTimeout(timeout);
    }
  }, [isSuccess]);

  const handleUploadClick = async () => {
    setProgress(0);
    setErrorData([]); // Clear previous errors
    setValidUserData([]); // Clear previous valid data
    setNoData(true); // Reset display

    if (!file) {
      notifyError("Please select a file to upload.");
      return;
    }

    // --- 1. Check for valid file type ---
    if (file.type !== "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") {
      notifyError("Only xlsx files are accepted.");
      return;
    }

    

    let allData: any[] = [];
    try {
      // Note: readXlsxFile reads the first sheet only, covering typical single-sheet template use.
      const fileData = await file.arrayBuffer();
      
      // Read all data from the first sheet
      allData = await readXlsxFile(fileData, {
        parseNumber: (string) => string,
      });

      const allSheets = await readSheetNames(file);

      if (allSheets.length !== 1) {
        notifyError("The file should contain only one sheet named UserData!");
        return;
      }

      if (allSheets[0] !== 'UserData') {
        notifyError("The sheet name in the file should be UserData!");
        return;
      }
      

    } catch (error) {
      // Handles cases where the file might be corrupted or unreadable (similar to 'blank file')
      notifyError("Could not read the file. It might be corrupted or empty.");
      return;
    }


    // --- 2. Check for No Data (Blank sheet content / Blank File) ---
    if (allData.length === 0) {
      notifyError("No data found in the file.");
      return;
    }

    const headers = allData[0];
    const dataRows = allData.slice(1);

    //  3. Validate Headers (Mismatches, Duplicates, Extra/Missing) 
    const lowerCaseHeaders = headers.map((h: string) => h ? h.trim().toLowerCase() : "");
    
    // Define lower case required headers for easier comparison
    const requiredLower = REQUIRED_HEADERS.map(h => h.toLowerCase());

    // 3a. Check for Missing Required Headers 
    const missingHeaders = requiredLower.filter(
        (rh) => !lowerCaseHeaders.includes(rh)
    );

    if (missingHeaders.length > 0) {
      notifyError(`Missing required headers: ${missingHeaders.join(", ")}.`);
      return;
    }
    
    // 3b. Check for Duplicate or Blank Headers (LOWER PRIORITY)
    const uniqueHeaders = new Set(lowerCaseHeaders.filter((h:any) => h !== ""));
    if (uniqueHeaders.size !== lowerCaseHeaders.length || lowerCaseHeaders.some((h:any) => h === "")) {
        notifyError("Duplicate or blank column headers found in the file.");
        return;
    }
    
    // 3c. Check for Extra Headers (if the column count must match exactly)
    if (headers.length !== REQUIRED_HEADERS.length) {
        const extraHeaders = lowerCaseHeaders.filter(
            (ch:any) => !requiredLower.includes(ch)
        );
        if (extraHeaders.length > 0) {
            notifyError(`The file contains extra headers not required: ${extraHeaders.join(", ")}.`);
            return;
        } 
    }
    
    //  4. Check for Data Rows Only (Header with no data) ---
    if (dataRows.length === 0) {
      notifyError(
        "Please enter at least one row of data apart from the header."
      );
      return;
    }

    //  5. Check Max Records Limit ---
    if (dataRows.length > MAX_RECORDS) {
      notifyError(`You can only upload a maximum of ${MAX_RECORDS} records at a time.`);
      return;
    }

    // Map the data rows using header indexing (resilient to column order changes)
    const userData = dataRows.map((row: any, index: number) => {
      // Find the index of the required headers in the uploaded file's headers
      const usernameIndex = lowerCaseHeaders.indexOf("username");
      const emailIndex = lowerCaseHeaders.indexOf("email id");
      const pwdIndex = lowerCaseHeaders.indexOf("password");

      return {
        id: index + 1, // Start IDs from 1 for data rows
        username: row[usernameIndex] ? String(row[usernameIndex]).trim() : "",
        email: row[emailIndex] ? String(row[emailIndex]).trim() : "",
        pwd: row[pwdIndex] ? String(row[pwdIndex]).trim() : "",
      };
    }).filter((user: any) => user.username || user.email || user.pwd); // Filter out entirely empty rows

    // Re-check for no actual data rows after filtering entirely empty ones
    if (userData.length === 0) {
        notifyError("All data rows were empty or contained only blank values.");
        return;
    }

    try {
      // 6. Server Validation Call ---
      const response = await postUsersDataForValidation({ userData });

      setNoData(false);
      
      if (response?.data?.ec && response?.data?.ec > 0) {
        if (response?.data.inv_ent) {
          const errorRowData = response?.data?.inv_ent?.map((row: any) => {
            return {
              error: row?.err,
              username: userData.find((u: any) => u.id === row.id)?.username || "",
              email: userData.find((u: any) => u.id === row.id)?.email || "",
              pwd: userData.find((u: any) => u.id === row.id)?.pwd || "",
              roles: null,
              permissions: null,
            };
          });

          setErrorData(errorRowData);
        }
        
        const validData = userData.filter((row: any) => {
          return !response?.data?.inv_ent?.some(
            (errorRow: any) => errorRow.id === row.id 
          );
        });

        validData.forEach((ele: any, index: number) => {
          ele.id = index + 1;
        });

        setValidUserData(validData);
        setNoData(false);
      } else {
        // All data is valid
        setValidUserData(userData);
        setNoData(false);
      }
    } catch (error: any) {
      notifyError("Failed to validate data!");
    }
  };

  const handleFileChange = (e: any) => {
    if (e?.target?.files?.length < 1) {
      return;
    }

    const file = e?.target?.files?.[0];
    switch (file?.type) {
      case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        setFile(file);
        break;
      default:
        notifyError("Only xlsx files are accepted");
    }
  };

  return (
    <UploadSectionWrapper>
      <UploadLeftSection
        setErrorCount={setErrorCount}
        setErrorData={setErrorData}
        setValidData={setValidUserData}
        setNoData={setNoData}
        handleUploadClick={handleUploadClick}
        handleFileChange={handleFileChange}
        file={file}
      />
      {noData ? (
        <NoDataToDisplay imgSrc={"/assets/img/no data to display.svg"} />
      ) : (
        <UploadRightSection
          errorCount={errorCount}
          errorData={errorData}
          validData={validUserData}
          setIsAssignPageOpen={setIsAssignPageOpen}
          progress={progress}
        />
      )}
    </UploadSectionWrapper>
  );
}

export default UploadWrapperSection;
