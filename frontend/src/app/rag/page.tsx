"use client";

import { useState } from "react";
import { MainLayout } from "@/components/layout/main-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MessageSquare, Loader2, BookOpen, Send } from "lucide-react";
import { useMutation } from "react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function RAGPage() {
  const [question, setQuestion] = useState("");
  const [bookTitle, setBookTitle] = useState("");
  const [result, setResult] = useState<any>(null);

  const askMutation = useMutation(
    () => api.askQuestion({ question, book_title: bookTitle || undefined }),
    {
      onSuccess: (data) => {
        setResult(data);
        toast.success("回答を取得しました!");
      },
      onError: (error: any) => {
        toast.error(error.message || "質問処理に失敗しました");
      },
    }
  );

  const handleAsk = () => {
    if (!question.trim()) {
      toast.error("質問を入力してください");
      return;
    }
    askMutation.mutate();
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">RAG検索</h2>
          <p className="mt-2 text-muted-foreground">
            抽出したテキストに対して自然言語で質問できます
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Question Section */}
          <Card>
            <CardHeader>
              <CardTitle>質問入力</CardTitle>
              <CardDescription>書籍の内容について質問してください</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">書籍タイトル (オプション)</label>
                <input
                  type="text"
                  value={bookTitle}
                  onChange={(e) => setBookTitle(e.target.value)}
                  placeholder="特定の書籍に絞り込む場合は入力"
                  className="mt-1.5 w-full rounded-md border px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="text-sm font-medium">質問</label>
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="例: この本の主要なテーマは何ですか?"
                  className="mt-1.5 h-32 w-full resize-none rounded-md border p-3 text-sm"
                />
              </div>

              <Button
                onClick={handleAsk}
                disabled={!question.trim() || askMutation.isLoading}
                className="w-full"
              >
                {askMutation.isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    処理中...
                  </>
                ) : (
                  <>
                    <Send className="mr-2 h-4 w-4" />
                    質問する
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Answer Section */}
          <Card>
            <CardHeader>
              <CardTitle>回答</CardTitle>
              <CardDescription>AIによる回答と参照元</CardDescription>
            </CardHeader>
            <CardContent>
              {askMutation.isLoading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <Loader2 className="h-12 w-12 animate-spin text-primary" />
                  <p className="mt-4 text-sm text-muted-foreground">回答を生成中...</p>
                </div>
              ) : result ? (
                <div className="space-y-4">
                  <div className="rounded-lg bg-blue-50 p-4">
                    <p className="text-sm leading-relaxed text-gray-900">{result.answer}</p>
                  </div>

                  {result.sources && result.sources.length > 0 && (
                    <div>
                      <h4 className="mb-3 text-sm font-semibold">参照元</h4>
                      <div className="space-y-2">
                        {result.sources.map((source: any, idx: number) => (
                          <div key={idx} className="rounded-lg border p-3 text-sm">
                            <div className="mb-2 flex items-center justify-between">
                              <span className="font-medium">ページ {source.page_num}</span>
                              <span className="text-xs text-muted-foreground">
                                信頼度: {(source.confidence * 100).toFixed(1)}%
                              </span>
                            </div>
                            <p className="text-xs text-gray-600">{source.text.substring(0, 150)}...</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <MessageSquare className="h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-sm text-muted-foreground">
                    質問を入力して「質問する」をクリックしてください
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Tips */}
        <Card>
          <CardHeader>
            <CardTitle>使い方のヒント</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex items-start space-x-3">
                <BookOpen className="mt-1 h-5 w-5 flex-shrink-0 text-primary" />
                <div>
                  <h4 className="font-medium">具体的な質問</h4>
                  <p className="mt-1 text-sm text-muted-foreground">
                    「この章の要点は?」のように具体的に質問すると、より正確な回答が得られます
                  </p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <MessageSquare className="mt-1 h-5 w-5 flex-shrink-0 text-primary" />
                <div>
                  <h4 className="font-medium">コンテキストを指定</h4>
                  <p className="mt-1 text-sm text-muted-foreground">
                    書籍タイトルを指定すると、その書籍に絞って検索できます
                  </p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <Send className="mt-1 h-5 w-5 flex-shrink-0 text-primary" />
                <div>
                  <h4 className="font-medium">複数の質問</h4>
                  <p className="mt-1 text-sm text-muted-foreground">
                    異なる視点から複数の質問をすることで、より深い理解が得られます
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
