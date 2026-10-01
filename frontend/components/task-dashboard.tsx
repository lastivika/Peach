import Link from "next/link";
import { ItemSummary } from "@/components/item-summary";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
export function TaskDashboard() {
  return (
    <div className="grid gap-8">
      <PageHeader
        icon="🍑"
        title="Your workspace"
        description="Make room for what matters. Here's how your tasks are coming along."
      />
      <ItemSummary />
      <Button asChild className="justify-self-start">
        <Link href="/items">Open board →</Link>
      </Button>
    </div>
  );
}
