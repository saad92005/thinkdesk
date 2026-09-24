import { cn } from "@/lib/cn";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={cn("h-7 w-7", className)} aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="var(--brand)" />
      <path
        d="M9 20.5V11.5C9 10.6716 9.67157 10 10.5 10H16C18.4853 10 20.5 12.0147 20.5 14.5C20.5 16.9853 18.4853 19 16 19H12.5"
        stroke="var(--brand-foreground)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12.5" cy="22" r="1.4" fill="var(--brand-foreground)" />
    </svg>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold tracking-tight", className)}>
      <LogoMark />
      <span>ThinkDesk</span>
    </span>
  );
}
