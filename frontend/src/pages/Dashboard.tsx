import { Boxes, FlaskConical, Package, TrendingUp } from "lucide-react";

import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { useAuth } from "@/hooks/useAuth";
import { useProjects } from "@/hooks/useProjects";

/** Landing dashboard with headline KPIs. */
export function Dashboard() {
  const { user } = useAuth();
  const { data: projects } = useProjects(1, 1);

  const stats = [
    { label: "Projects", value: projects?.meta.total ?? "—", icon: Boxes, tone: "text-brand-600" },
    { label: "Experiments", value: "—", icon: FlaskConical, tone: "text-purple-600" },
    { label: "Models", value: "—", icon: Package, tone: "text-green-600" },
    { label: "Deployed", value: "—", icon: TrendingUp, tone: "text-amber-600" },
  ];

  return (
    <div>
      <PageHeader
        title={`Welcome back${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}`}
        description="Your AutoML workspace at a glance."
      />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, tone }) => (
          <Card key={label} className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">
                  {value}
                </p>
              </div>
              <Icon className={`h-8 w-8 ${tone}`} />
            </div>
          </Card>
        ))}
      </div>

      <Card className="mt-6 p-6">
        <h2 className="font-semibold text-slate-900 dark:text-slate-100">Getting started</h2>
        <ol className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-400">
          <li>1. Create a project to organise your work.</li>
          <li>2. Upload a CSV or Excel dataset — statistics are computed automatically.</li>
          <li>3. Launch an experiment to train and tune many models at once.</li>
          <li>4. Register the best run and deploy it to serve predictions.</li>
        </ol>
      </Card>
    </div>
  );
}
