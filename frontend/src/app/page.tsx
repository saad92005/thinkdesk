import {
  Bot,
  Check,
  ExternalLink,
  GitMerge,
  Plug,
  Quote,
  ShieldCheck,
  Upload,
  MessagesSquare,
  Zap,
} from "lucide-react";
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
    icon: Bot,
    title: "AI agents you actually control",
    description:
      "Ask the agent to draft a summary from Gmail or a document — nothing reaches Slack until you review and explicitly approve it.",
  },
  {
    icon: Zap,
    title: "Automation that proposes, not acts",
    description:
      "Save a rule once, run it whenever you like. It only ever queues a draft for your approval — automation without giving up control.",
  },
  {
    icon: Plug,
    title: "Connects to the tools you use",
    description:
      "Gmail, Slack, and Notion — read your own data in, act only with your explicit sign-off.",
  },
  {
    icon: ShieldCheck,
    title: "Workspace-isolated by design",
    description:
      "Every team gets its own workspace with role-based access. Authorization is enforced before any document is ever touched — never left to the model to decide.",
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

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Everything you need to try ThinkDesk for real, on your own documents.",
    features: [
      "Up to 3 documents",
      "Up to 50 chat messages",
      "Hybrid search + citations",
      "Research mode",
      "Gmail, Slack & Notion connectors",
    ],
    cta: { href: "/signup", label: "Get started free", variant: "secondary" as const },
  },
  {
    name: "Pro",
    price: "$9.99",
    period: "/ month",
    description: "For teams putting ThinkDesk into daily use.",
    features: [
      "Unlimited documents",
      "Unlimited chat messages",
      "AI agent actions & automation rules",
      "Document comparison & reports",
      "Priority support",
    ],
    cta: { href: "/signup", label: "Start free, upgrade anytime", variant: "primary" as const },
    highlighted: true,
  },
];

export default function Home() {
  return (
    <>
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-border bg-background/80 px-6 py-5 backdrop-blur-md sm:px-10">
        <Logo />
        <nav className="hidden items-center gap-8 text-sm font-medium text-muted md:flex">
          <a href="#features" className="transition-colors hover:text-foreground">
            Features
          </a>
          <a href="#pricing" className="transition-colors hover:text-foreground">
            Pricing
          </a>
          <a
            href="https://github.com/saad92005/thinkdesk"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 transition-colors hover:text-foreground"
          >
            GitHub <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </nav>
        <AuthStatus />
      </header>

      <main className="flex-1">
        <section className="relative overflow-hidden">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 -z-10"
            style={{
              background:
                "radial-gradient(60% 50% at 50% 0%, var(--brand-soft) 0%, transparent 70%)",
            }}
          />
          <div className="mx-auto max-w-3xl px-6 pt-20 pb-20 text-center sm:pt-28">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted shadow-sm">
              <Zap className="h-3.5 w-3.5 text-brand" /> Now with AI agents & automation
            </span>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              Ask your documents anything —{" "}
              <span className="bg-gradient-to-r from-brand to-indigo-400 bg-clip-text text-transparent">
                get answers you can verify.
              </span>
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-lg text-muted text-balance">
              ThinkDesk is an AI knowledge workspace: search your documents with real citations, research
              across your whole knowledge base, and let AI agents take approved actions — never guessed,
              never unsupervised.
            </p>
            <div className="mt-8 flex items-center justify-center gap-3">
              <LinkButton href="/signup" size="lg">
                Get started free
              </LinkButton>
              <LinkButton href="/login" variant="secondary" size="lg">
                Log in
              </LinkButton>
            </div>
            <p className="mt-4 text-xs text-muted">No credit card required · Free plan available forever</p>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-5xl px-6 pb-20 scroll-mt-20">
          <div className="mx-auto max-w-xl text-center">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">A complete AI knowledge platform</h2>
            <p className="mt-3 text-muted">Not just "chat with your PDF" — retrieval, intelligence, agents, and automation, all grounded in your own data.</p>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <Card key={feature.title} className="p-6 transition-shadow hover:shadow-md">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-soft text-brand">
                  <feature.icon className="h-5 w-5" strokeWidth={1.5} />
                </div>
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

        <section id="pricing" className="mx-auto max-w-4xl px-6 py-20 scroll-mt-20">
          <div className="mx-auto max-w-xl text-center">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Simple, honest pricing</h2>
            <p className="mt-3 text-muted">Start free. Upgrade only when you actually need more room.</p>
          </div>
          <div className="mt-10 grid gap-6 sm:grid-cols-2">
            {PLANS.map((plan) => (
              <Card
                key={plan.name}
                className={
                  plan.highlighted
                    ? "relative border-brand p-6 shadow-md ring-1 ring-brand"
                    : "relative p-6"
                }
              >
                {plan.highlighted && (
                  <span className="absolute -top-3 left-6 rounded-full bg-brand px-3 py-1 text-xs font-medium text-brand-foreground">
                    Most popular
                  </span>
                )}
                <h3 className="font-semibold text-foreground">{plan.name}</h3>
                <p className="mt-2 flex items-baseline gap-1">
                  <span className="text-3xl font-semibold tracking-tight text-foreground">{plan.price}</span>
                  <span className="text-sm text-muted">{plan.period}</span>
                </p>
                <p className="mt-2 text-sm text-muted">{plan.description}</p>
                <ul className="mt-5 flex flex-col gap-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-foreground">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand" /> {f}
                    </li>
                  ))}
                </ul>
                <div className="mt-6">
                  <LinkButton href={plan.cta.href} variant={plan.cta.variant} className="w-full justify-center">
                    {plan.cta.label}
                  </LinkButton>
                </div>
              </Card>
            ))}
          </div>
        </section>

        <section className="border-t border-border py-20 text-center">
          <div className="mx-auto max-w-3xl px-6">
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
          </div>
        </section>
      </main>

      <footer className="border-t border-border px-6 py-8 text-center text-sm text-muted">
        © {new Date().getFullYear()} ThinkDesk. Built as an AI-powered knowledge workspace.
      </footer>
    </>
  );
}
