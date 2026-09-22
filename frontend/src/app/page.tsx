import { AuthStatus } from "@/components/auth-status";
import { HealthStatus } from "@/components/health-status";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="space-y-2">
        <h1 className="text-4xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-100">
          THINKDESK
        </h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Your knowledge. Your AI workspace.
        </p>
      </div>
      <AuthStatus />
      <HealthStatus />
    </main>
  );
}
