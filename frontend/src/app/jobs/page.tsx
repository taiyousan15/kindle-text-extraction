"use client";

import { useState } from "react";
import { MainLayout } from "@/components/layout/main-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useQuery } from "react-query";
import { api } from "@/lib/api";
import { formatDate, getStatusColor } from "@/lib/utils";
import { Loader2, Filter, Download, CheckCircle, XCircle, Clock } from "lucide-react";

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [limit, setLimit] = useState(20);

  const { data: allJobs, isLoading, refetch } = useQuery(
    ["jobs", limit],
    () => api.listJobs(limit),
    {
      refetchInterval: 5000,
    }
  );

  const filteredJobs = allJobs?.filter(
    (job) => statusFilter === "all" || job.status === statusFilter
  );

  const stats = allJobs
    ? {
        total: allJobs.length,
        completed: allJobs.filter((j) => j.status === "completed").length,
        processing: allJobs.filter((j) => j.status === "processing").length,
        failed: allJobs.filter((j) => j.status === "failed").length,
      }
    : null;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case "failed":
        return <XCircle className="h-5 w-5 text-red-600" />;
      case "processing":
        return <Loader2 className="h-5 w-5 animate-spin text-blue-600" />;
      default:
        return <Clock className="h-5 w-5 text-yellow-600" />;
    }
  };

  const exportToCSV = () => {
    if (!filteredJobs) return;

    const headers = ["Job ID", "Book Title", "Status", "Progress", "Pages", "Created At", "Completed At"];
    const rows = filteredJobs.map((job) => [
      job.job_id,
      job.book_title || "",
      job.status,
      job.progress,
      job.pages_captured,
      job.created_at,
      job.completed_at || "",
    ]);

    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kindle_ocr_jobs_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">ジョブ管理</h2>
            <p className="mt-2 text-muted-foreground">すべてのOCRジョブを管理・監視</p>
          </div>
          <div className="flex space-x-2">
            <Button variant="outline" onClick={() => refetch()}>
              <Loader2 className="mr-2 h-4 w-4" />
              更新
            </Button>
            <Button variant="outline" onClick={exportToCSV}>
              <Download className="mr-2 h-4 w-4" />
              CSV出力
            </Button>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="p-6">
                <div className="text-2xl font-bold">{stats.total}</div>
                <p className="text-xs text-muted-foreground">総ジョブ数</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
                <p className="text-xs text-muted-foreground">完了</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="text-2xl font-bold text-blue-600">{stats.processing}</div>
                <p className="text-xs text-muted-foreground">処理中</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
                <p className="text-xs text-muted-foreground">失敗</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Filter className="mr-2 h-5 w-5" />
              フィルター
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-4">
              <div className="flex-1">
                <label className="text-sm font-medium">ステータス</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="mt-1.5 w-full rounded-md border px-3 py-2 text-sm"
                >
                  <option value="all">すべて</option>
                  <option value="pending">待機中</option>
                  <option value="processing">処理中</option>
                  <option value="completed">完了</option>
                  <option value="failed">失敗</option>
                </select>
              </div>
              <div className="flex-1">
                <label className="text-sm font-medium">表示件数</label>
                <select
                  value={limit}
                  onChange={(e) => setLimit(parseInt(e.target.value))}
                  className="mt-1.5 w-full rounded-md border px-3 py-2 text-sm"
                >
                  <option value={10}>10件</option>
                  <option value={20}>20件</option>
                  <option value={50}>50件</option>
                  <option value={100}>100件</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Jobs List */}
        <Card>
          <CardHeader>
            <CardTitle>ジョブ一覧</CardTitle>
            <CardDescription>
              {filteredJobs?.length || 0}件のジョブを表示中
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
              </div>
            ) : filteredJobs && filteredJobs.length > 0 ? (
              <div className="space-y-3">
                {filteredJobs.map((job) => (
                  <div
                    key={job.job_id}
                    className="rounded-lg border p-4 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-4">
                        {getStatusIcon(job.status)}
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <h3 className="font-semibold">{job.book_title || "無題"}</h3>
                            <span
                              className={`rounded-full px-2 py-0.5 text-xs ${getStatusColor(
                                job.status
                              )}`}
                            >
                              {job.status}
                            </span>
                          </div>
                          <div className="mt-1 space-y-1 text-sm text-muted-foreground">
                            <p>ジョブID: {job.job_id.substring(0, 8)}...</p>
                            <p>
                              {job.pages_captured}ページ • 作成: {formatDate(job.created_at)}
                            </p>
                            {job.completed_at && (
                              <p>完了: {formatDate(job.completed_at)}</p>
                            )}
                            {job.error_message && (
                              <p className="text-red-600">エラー: {job.error_message}</p>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="ml-4 flex flex-col items-end">
                        <div className="text-2xl font-bold">{job.progress}%</div>
                        <div className="mt-2 h-2 w-32 rounded-full bg-gray-200">
                          <div
                            className={`h-full rounded-full ${
                              job.status === "failed"
                                ? "bg-red-500"
                                : job.status === "completed"
                                ? "bg-green-500"
                                : "bg-blue-500"
                            }`}
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center text-muted-foreground">
                {statusFilter === "all"
                  ? "ジョブがありません"
                  : `${statusFilter}のジョブがありません`}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
