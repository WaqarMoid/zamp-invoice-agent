/**
 * Formatting utilities conforming to docs/09 §9.7 and §9.11
 */

const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatMoney(val: number | string | null | undefined): string {
  if (val === null || val === undefined || val === "") return "—";
  const num = typeof val === "number" ? val : parseFloat(val);
  if (isNaN(num)) return "—";
  return inrFormatter.format(num);
}

export function formatCompactMoney(val: number | string | null | undefined): string {
  if (val === null || val === undefined || val === "") return "—";
  const num = typeof val === "number" ? val : parseFloat(val);
  if (isNaN(num)) return "—";

  if (num >= 10000000) {
    const cr = num / 10000000;
    return `₹${cr.toFixed(2)} Cr`;
  }
  if (num >= 100000) {
    const l = num / 100000;
    return `₹${l.toFixed(1)} L`;
  }
  return formatMoney(num);
}

export function formatDate(isoStr: string | null | undefined): string {
  if (!isoStr) return "—";
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    const day = d.getDate();
    const months = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];
    const month = months[d.getMonth()];
    const year = d.getFullYear();
    return `${day} ${month} ${year}`;
  } catch {
    return isoStr;
  }
}

export function formatRelativeTime(isoStr: string | null | undefined): string {
  if (!isoStr) return "—";
  try {
    const d = new Date(isoStr);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);

    if (diffSec < 60) return "just now";
    if (diffSec < 3600) {
      const m = Math.floor(diffSec / 60);
      return `${m} min ago`;
    }
    if (diffSec < 86400) {
      const h = Math.floor(diffSec / 3600);
      return `${h} ${h === 1 ? "hour" : "hours"} ago`;
    }
    return formatDate(isoStr);
  } catch {
    return isoStr;
  }
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  const sec = (ms / 1000).toFixed(1);
  return `${sec} s`;
}
