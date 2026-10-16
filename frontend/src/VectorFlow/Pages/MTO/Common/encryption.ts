import CryptoJS from "crypto-js";
 
const SECRET_PHRASE = process.env.REACT_APP_SECRET_KEY || "mykey123";
 
function stringifyData(value: any): string {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
 
export function encryptStorageData(data: any): string {
  try {
    const dataString = stringifyData(data);
 
    const encrypted = CryptoJS.AES.encrypt(dataString, SECRET_PHRASE);
    return encrypted.toString();
  } catch (err) {
    console.error("Encryption failed:", err);
    return "";
  }
}
 
export function decryptStorageData(encryptedData: string | null): any | null {
  if (!encryptedData || typeof encryptedData !== "string") return null;
 
  try {
    const decrypted = CryptoJS.AES.decrypt(encryptedData, SECRET_PHRASE);
    const originalText = decrypted.toString(CryptoJS.enc.Utf8);
 
    if (!originalText || originalText.trim() === "" || typeof originalText === "object") {
      return null;
    }
 
    try {
      return JSON.parse(originalText);
    } catch {
      return originalText;
    }
  } catch (error) {
    // Values written by an older build can use a different local-storage key.
    // Treat those values as an ordinary cache miss so a deployment upgrade does
    // not flood the console or prevent the current menu from being rendered.
    return null;
  }
}
