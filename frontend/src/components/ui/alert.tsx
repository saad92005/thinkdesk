import { cn } from "@/lib/cn";

export function Alert({ tone = "danger", children }: { tone?: "danger" | "info"; children: React.ReactNode }) {
  return (
    <p
      role="alert"
      className={cn(
        "rounded-lg border px-3 py-2 text-sm",
        tone === "danger"
          ? "border-red-500/20 bg-red-500/10 text-red-600 dark:text-red-400"
          : "border-blue-500/20 bg-blue-500/10 text-blue-600 dark:text-blue-400"
      )}
    >
      {children}
    </p>
  );
}
