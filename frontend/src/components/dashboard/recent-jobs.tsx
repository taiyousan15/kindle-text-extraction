"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "react-query";
import { api } from "@/lib/api";
import { formatDate, getStatusColor } from "@/lib/utils";
import { Clock, CheckCircle, XCircle, Loader2 } from "lucide-react";

export function RecentJobs() {
  const { data: jobs, isLoading } = useQuery("recentJobs", () => api.listJobs(5));

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-600" />;
      case "processing":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-600" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-600" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>最近のジョブ</CardTitle>
        <CardDescription>直近5件のOCRジョブを表示</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : Array.isArray(jobs) && jobs.length > 0 ? (
          <div className="space-y-4">
            {jobs.map((job) => (
              <div
                key={job?.job_id ?? `job-${Math.random()}`}
                className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <div className="flex items-center space-x-4">
                  {getStatusIcon(job?.status ?? "pending")}
                  <div>
                    <p className="font-medium">{job?.book_title ?? "無題"}</p>
                    <div className="mt-1 flex items-center space-x-2 text-sm text-muted-foreground">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${getStatusColor(job?.status ?? "pending")}`}>
                        {job?.status ?? "不明"}
                      </span>
                      <span>{job?.pages_captured ?? 0}ページ</span>
                      <span>•</span>
                      <span>{job?.created_at ? formatDate(job.created_at) : "不明"}</span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">{job?.progress ?? 0}%</p>
                  <div className="mt-1 h-1.5 w-20 rounded-full bg-gray-200">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${job?.progress ?? 0}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-8 text-center text-sm text-muted-foreground">
            まだジョブがありません
          </div>
        )}
      </CardContent>
    </Card>
  );
}
