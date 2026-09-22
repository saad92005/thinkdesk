import { useEffect, useState } from "react";
import { listOrganizations, type Organization } from "@/lib/api";

/** undefined = still loading, null = not found / not a member */
export function useOrganization(orgId: string): Organization | null | undefined {
  const [org, setOrg] = useState<Organization | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    listOrganizations().then((orgs) => {
      if (cancelled) return;
      setOrg(orgs.find((o) => o.id === orgId) ?? null);
    });
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  return org;
}
