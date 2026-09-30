declare module "react-simple-captcha" {
  export function loadCaptchaEnginge(length?: number): void;
  export function validateCaptcha(value: string, reload?: boolean): boolean;
  export const LoadCanvasTemplate: React.ComponentType;
  export const LoadCanvasTemplateNoReload: React.ComponentType;
}
