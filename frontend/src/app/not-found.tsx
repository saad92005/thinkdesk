import { LinkButton } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";

export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
      <Logo />
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Page not found</h1>
        <p className="mt-1 text-sm text-muted">The page you&apos;re looking for doesn&apos;t exist.</p>
      </div>
      <LinkButton href="/">Back to home</LinkButton>
    </main>
  );
}
