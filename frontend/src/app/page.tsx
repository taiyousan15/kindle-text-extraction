"use client";

import { MainLayout } from "@/components/layout/main-layout";
import { StatsCard } from "@/components/dashboard/stats-card";
import { RecentJobs } from "@/components/dashboard/recent-jobs";
import { useQuery } from "react-query";
import { api } from "@/lib/api";
import { FileText, CheckCircle, Loader2, XCircle, BookOpen } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function HomePage() {
  const { data: jobs } = useQuery("jobs", () => api.listJobs(100));

  const stats = Array.isArray(jobs)
    ? {
        totalJobs: jobs.length,
        completedJobs: jobs.filter((j) => j?.status === "completed").length,
        processingJobs: jobs.filter((j) => j?.status === "processing").length,
        failedJobs: jobs.filter((j) => j?.status === "failed").length,
        totalPages: jobs.reduce((acc, j) => acc + (j?.pages_captured ?? 0), 0),
        successRate: jobs.length > 0
          ? Math.round((jobs.filter((j) => j?.status === "completed").length / jobs.length) * 100)
          : 0,
      }
    : null;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Welcome Section */}
        <div>
          <h2 className="text-3xl font-bold tracking-tight">ダッシュボード</h2>
          <p className="mt-2 text-muted-foreground">
            Kindle OCRシステムへようこそ。書籍のテキスト抽出とRAG検索を簡単に行えます。
          </p>
        </div>

        {/* Stats Grid */}
        {stats && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatsCard
              title="総ジョブ数"
              value={stats.totalJobs}
              icon={FileText}
              description="すべてのOCRジョブ"
            />
            <StatsCard
              title="完了"
              value={stats.completedJobs}
              icon={CheckCircle}
              description="正常に完了したジョブ"
            />
            <StatsCard
              title="処理中"
              value={stats.processingJobs}
              icon={Loader2}
              description="現在実行中のジョブ"
            />
            <StatsCard
              title="OCRページ数"
              value={stats.totalPages}
              icon={BookOpen}
              description="抽出済みページ数"
            />
          </div>
        )}

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>クイックアクション</CardTitle>
            <CardDescription>よく使う機能へ素早くアクセス</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <Link href="/upload">
                <Button variant="outline" className="h-24 w-full flex-col">
                  <FileText className="mb-2 h-8 w-8" />
                  <span className="font-semibold">画像をアップロード</span>
                  <span className="text-xs text-muted-foreground">手動OCR処理</span>
                </Button>
              </Link>
              <Link href="/capture">
                <Button variant="outline" className="h-24 w-full flex-col">
                  <Loader2 className="mb-2 h-8 w-8" />
                  <span className="font-semibold">自動キャプチャ</span>
                  <span className="text-xs text-muted-foreground">複数ページを一括処理</span>
                </Button>
              </Link>
              <Link href="/rag">
                <Button variant="outline" className="h-24 w-full flex-col">
                  <BookOpen className="mb-2 h-8 w-8" />
                  <span className="font-semibold">RAG検索</span>
                  <span className="text-xs text-muted-foreground">書籍に質問する</span>
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Recent Jobs */}
        <RecentJobs />

        {/* System Info */}
        {stats && (
          <Card>
            <CardHeader>
              <CardTitle>システム情報</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">成功率</p>
                  <p className="mt-1 text-2xl font-bold">{stats.successRate}%</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">失敗ジョブ</p>
                  <p className="mt-1 text-2xl font-bold text-red-600">{stats.failedJobs}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">平均ページ数</p>
                  <p className="mt-1 text-2xl font-bold">
                    {stats.totalJobs > 0 ? Math.round(stats.totalPages / stats.totalJobs) : 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
