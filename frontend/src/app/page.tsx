import { FileSearch, GitMerge, Quote, ShieldCheck, Upload, MessagesSquare } from "lucide-react";
import { AuthStatus } from "@/components/auth-status";
import { Logo } from "@/components/ui/logo";
import { LinkButton } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Quote,
    title: "Real citations, every time",
    description:
      "Every answer is built directly from the documents that were actually retrieved — never parsed out of what the model claims. Click through to the exact page.",
  },
  {
    icon: GitMerge,
    title: "Hybrid retrieval",
    description:
      "Vector search and keyword (BM25) search run together and get fused with reciprocal rank fusion, so exact terms and paraphrased questions both work.",
  },
  {
    icon: ShieldCheck,
    title: "Workspace-isolated by design",
    description:
      "Every team gets its own workspace with role-based access. Authorization is enforced before any document is ever touched — never left to the model to decide.",
  },
  {
    icon: FileSearch,
    title: "Grounded, not guessed",
    description:
      "If nothing relevant is found in your documents, ThinkDesk says so — it never fabricates an answer to fill the silence.",
  },
];

const STEPS = [
  {
    icon: Upload,
    title: "Upload your documents",
    description: "Drop in a PDF. It's extracted, chunked, and embedded automatically in the background.",
  },
  {
    icon: MessagesSquare,
    title: "Ask a question",
    description: "Ask in plain language. ThinkDesk retrieves the most relevant passages across your knowledge base.",
  },
  {
    icon: Quote,
    title: "Get a cited answer",
    description: "Read a grounded answer with links back to the exact source passages it came from.",
  },
];

export default function Home() {
  return (
    <>
      <header className="flex items-center justify-between px-6 py-5 sm:px-10">
        <Logo />
        <AuthStatus />
      </header>

      <main className="flex-1">
        <section className="mx-auto max-w-3xl px-6 pt-16 pb-20 text-center sm:pt-24">
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Ask your documents anything —{" "}
            <span className="text-brand">get answers you can verify.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg text-muted text-balance">
            ThinkDesk is an AI knowledge workspace. Upload your documents, ask questions in plain
            language, and get evidence-backed answers with real citations — not a chatbot guessing
            from thin air.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <LinkButton href="/signup" size="lg">
              Get started free
            </LinkButton>
            <LinkButton href="/login" variant="secondary" size="lg">
              Log in
            </LinkButton>
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-20">
          <div className="grid gap-5 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <Card key={feature.title} className="p-6">
                <feature.icon className="h-8 w-8 text-brand" strokeWidth={1.5} />
                <h3 className="mt-4 font-semibold text-foreground">{feature.title}</h3>
                <p className="mt-1.5 text-sm text-muted">{feature.description}</p>
              </Card>
            ))}
          </div>
        </section>

        <section className="border-t border-border bg-surface py-20">
          <div className="mx-auto max-w-5xl px-6">
            <h2 className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">How it works</h2>
            <div className="mt-12 grid gap-10 sm:grid-cols-3">
              {STEPS.map((step, index) => (
                <div key={step.title} className="text-center">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft text-brand">
                    <step.icon className="h-6 w-6" strokeWidth={1.5} />
                  </div>
                  <p className="mt-4 text-sm font-medium text-muted">Step {index + 1}</p>
                  <h3 className="mt-1 font-semibold text-foreground">{step.title}</h3>
                  <p className="mt-1.5 text-sm text-muted">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-3xl px-6 py-20 text-center">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Stop searching. Start asking.
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-muted">
            Create a free workspace and upload your first document in under a minute.
          </p>
          <div className="mt-6">
            <LinkButton href="/signup" size="lg">
              Get started free
            </LinkButton>
          </div>
        </section>
      </main>

      <footer className="border-t border-border px-6 py-8 text-center text-sm text-muted">
        © {new Date().getFullYear()} ThinkDesk. Built as an AI-powered knowledge workspace.
      </footer>
    </>
  );
}
