// The server decides this temporary local policy. Failure retains the CAPTCHA.
export async function fixtureCaptchaExempt(email: string): Promise<boolean> {
  if (window.location.origin !== 'http://localhost:3006') return false;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 3000);
  try {
    const response = await fetch('/api/user/captcha-policy/', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }), cache: 'no-store',
      // This unauthenticated decision must also work with expired login cookies.
      credentials: 'omit', signal: controller.signal,
    });
    if (response.status !== 200) return false;
    const result = await response.json();
    return result !== null && typeof result === 'object'
      && Object.keys(result).length === 1 && result.exempt === true;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}
