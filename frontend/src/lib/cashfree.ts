/** Loads Cashfree's checkout script on demand (only on the pay page). */

interface CashfreeCheckout {
  checkout(options: { paymentSessionId: string; redirectTarget?: "_self" | "_blank" | "_top" | "_modal" }): Promise<unknown>;
}

declare global {
  interface Window {
    Cashfree?: (options: { mode: "sandbox" | "production" }) => CashfreeCheckout;
  }
}

const SDK_URL = "https://sdk.cashfree.com/js/v3/cashfree.js";
let loading: Promise<void> | null = null;

function loadScript(): Promise<void> {
  if (window.Cashfree) return Promise.resolve();
  loading ??= new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SDK_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loading = null;
      reject(new Error("Could not load the payment page. Check your internet connection and try again."));
    };
    document.head.appendChild(script);
  });
  return loading;
}

export async function openCashfreeCheckout(paymentSessionId: string, mode: string) {
  await loadScript();
  if (!window.Cashfree) throw new Error("The payment page did not load. Please try again.");
  const cashfree = window.Cashfree({ mode: mode === "production" ? "production" : "sandbox" });
  await cashfree.checkout({ paymentSessionId, redirectTarget: "_self" });
}
