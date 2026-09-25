"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CreditCard } from "lucide-react";
import { OrgNav } from "@/components/org-nav";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import {
  ApiError,
  createCheckout,
  getSubscription,
  type OrganizationRole,
  type Subscription,
  type SubscriptionStatus,
} from "@/lib/api";
import { useOrganization } from "@/lib/useOrganization";

const CAN_MANAGE: OrganizationRole[] = ["owner", "admin"];

const STATUS_TONE: Record<SubscriptionStatus, "success" | "warning" | "danger" | "neutral"> = {
  active: "success",
  on_trial: "success",
  past_due: "warning",
  paused: "warning",
  unpaid: "danger",
  cancelled: "danger",
  expired: "danger",
};

function formatDate(value: string | null): string | null {
  if (!value) return null;
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

export default function BillingPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const org = useOrganization(orgId);
  const [subscription, setSubscription] = useState<Subscription | null | undefined>(undefined);
  const [redirecting, setRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSubscription(orgId)
      .then(setSubscription)
      .catch(() => setSubscription(null));
  }, [orgId]);

  async function handleSubscribe() {
    setError(null);
    setRedirecting(true);
    try {
      const url = await createCheckout(orgId);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start checkout");
      setRedirecting(false);
    }
  }

  if (org === undefined || subscription === undefined) return <PageSpinner />;
  if (org === null) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-red-500">You don&apos;t have access to this workspace.</p>
      </main>
    );
  }

  const canManage = CAN_MANAGE.includes(org.role);

  return (
    <>
      <OrgNav orgId={orgId} orgName={org.name} />
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-foreground">
            <CreditCard className="h-5 w-5 text-brand" />
            Billing
          </h1>
          <p className="mt-1 text-sm text-muted">
            Real checkout via Lemon Squeezy — no fake &quot;Upgrade&quot; button, this actually charges a card.
          </p>
        </div>

        {error && <Alert>{error}</Alert>}

        {subscription ? (
          <Card className="flex flex-col gap-3 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">{subscription.variant_name}</p>
                <p className="text-xs text-muted">
                  {subscription.status === "cancelled" && subscription.ends_at
                    ? `Access until ${formatDate(subscription.ends_at)}`
                    : subscription.renews_at
                      ? `Renews ${formatDate(subscription.renews_at)}`
                      : null}
                </p>
              </div>
              <Badge tone={STATUS_TONE[subscription.status]}>{subscription.status.replace("_", " ")}</Badge>
            </div>
          </Card>
        ) : (
          <Card className="flex flex-col gap-4 p-6">
            <div>
              <p className="text-lg font-semibold text-foreground">Pro</p>
              <p className="text-sm text-muted">Unlock the full workspace for your team.</p>
            </div>
            {canManage ? (
              <Button onClick={handleSubscribe} disabled={redirecting} className="self-start">
                {redirecting && <Spinner className="h-4 w-4" />}
                Subscribe
              </Button>
            ) : (
              <p className="text-xs text-muted">Only owners and admins can manage billing.</p>
            )}
          </Card>
        )}
      </main>
    </>
  );
}
