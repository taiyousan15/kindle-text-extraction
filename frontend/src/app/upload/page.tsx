"use client";

import { useState } from "react";
import { MainLayout } from "@/components/layout/main-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Loader2, Check, X } from "lucide-react";
import { useMutation } from "react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { formatBytes, getConfidenceColor } from "@/lib/utils";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [bookTitle, setBookTitle] = useState("");
  const [pageNum, setPageNum] = useState(1);
  const [result, setResult] = useState<any>(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      "image/*": [".png", ".jpg", ".jpeg"],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
    onDrop: (acceptedFiles) => {
      const file = acceptedFiles[0];
      if (file) {
        setFile(file);
        setResult(null);
        const reader = new FileReader();
        reader.onload = () => setPreview(reader.result as string);
        reader.readAsDataURL(file);
      }
    },
  });

  const uploadMutation = useMutation(
    () => {
      if (!file) throw new Error("ファイルが選択されていません");
      return api.uploadImage(file, bookTitle, pageNum);
    },
    {
      onSuccess: (data) => {
        setResult(data);
        toast.success("OCR処理が完了しました!");
      },
      onError: (error: any) => {
        toast.error(error.message || "OCR処理に失敗しました");
      },
    }
  );

  const handleUpload = () => {
    if (!file) {
      toast.error("ファイルを選択してください");
      return;
    }
    if (!bookTitle.trim()) {
      toast.error("書籍タイトルを入力してください");
      return;
    }
    uploadMutation.mutate();
  };

  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setBookTitle("");
    setPageNum(1);
    setResult(null);
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">OCRアップロード</h2>
          <p className="mt-2 text-muted-foreground">
            画像ファイルをアップロードして、テキストを抽出します
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Upload Section */}
          <Card>
            <CardHeader>
              <CardTitle>ファイルアップロード</CardTitle>
              <CardDescription>PNG、JPG、JPEG形式の画像をアップロード (最大10MB)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Dropzone */}
              <div
                {...getRootProps()}
                className={`cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
                  isDragActive
                    ? "border-primary bg-primary/5"
                    : "border-gray-300 hover:border-primary/50"
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="mx-auto h-12 w-12 text-gray-400" />
                <p className="mt-4 text-sm font-medium">
                  {isDragActive ? "ファイルをドロップ" : "クリックまたはドラッグ&ドロップ"}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  PNG, JPG, JPEG (最大10MB)
                </p>
              </div>

              {/* Preview */}
              {preview && (
                <div className="rounded-lg border p-4">
                  <img src={preview} alt="Preview" className="mx-auto max-h-64 rounded" />
                  <div className="mt-4 space-y-2 text-sm">
                    <p>
                      <span className="font-medium">ファイル名:</span> {file?.name}
                    </p>
                    <p>
                      <span className="font-medium">サイズ:</span> {formatBytes(file?.size || 0)}
                    </p>
                  </div>
                </div>
              )}

              {/* Settings */}
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">書籍タイトル</label>
                  <input
                    type="text"
                    value={bookTitle}
                    onChange={(e) => setBookTitle(e.target.value)}
                    placeholder="例: プロンプトエンジニアリング入門"
                    className="mt-1.5 w-full rounded-md border px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">ページ番号</label>
                  <input
                    type="number"
                    value={pageNum}
                    onChange={(e) => setPageNum(parseInt(e.target.value) || 1)}
                    min={1}
                    max={10000}
                    className="mt-1.5 w-full rounded-md border px-3 py-2 text-sm"
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="flex space-x-2">
                <Button
                  onClick={handleUpload}
                  disabled={!file || !bookTitle.trim() || uploadMutation.isLoading}
                  className="flex-1"
                >
                  {uploadMutation.isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      処理中...
                    </>
                  ) : (
                    <>
                      <FileText className="mr-2 h-4 w-4" />
                      OCR実行
                    </>
                  )}
                </Button>
                <Button onClick={handleReset} variant="outline">
                  リセット
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Results Section */}
          <Card>
            <CardHeader>
              <CardTitle>OCR結果</CardTitle>
              <CardDescription>抽出されたテキストと信頼度</CardDescription>
            </CardHeader>
            <CardContent>
              {uploadMutation.isLoading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <Loader2 className="h-12 w-12 animate-spin text-primary" />
                  <p className="mt-4 text-sm text-muted-foreground">OCR処理中...</p>
                </div>
              ) : result ? (
                <div className="space-y-4">
                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-lg border p-4">
                      <p className="text-xs font-medium text-muted-foreground">信頼度</p>
                      <p className={`mt-1 text-2xl font-bold ${getConfidenceColor(result.confidence)}`}>
                        {(result.confidence * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div className="rounded-lg border p-4">
                      <p className="text-xs font-medium text-muted-foreground">文字数</p>
                      <p className="mt-1 text-2xl font-bold">{result.text.length}</p>
                    </div>
                  </div>

                  {/* Status */}
                  <div className="flex items-center space-x-2 rounded-lg bg-green-50 p-3 text-sm">
                    <Check className="h-4 w-4 text-green-600" />
                    <span className="font-medium text-green-900">OCR処理完了</span>
                  </div>

                  {/* Text */}
                  <div>
                    <label className="text-sm font-medium">抽出テキスト</label>
                    <textarea
                      value={result.text}
                      readOnly
                      className="mt-1.5 h-64 w-full resize-none rounded-md border p-3 text-sm"
                    />
                  </div>

                  {/* Download */}
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      const blob = new Blob([result.text], { type: "text/plain" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `${bookTitle}_page${pageNum}.txt`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    テキストをダウンロード
                  </Button>

                  {/* Confidence Warning */}
                  {result.confidence < 0.6 && (
                    <div className="flex items-start space-x-2 rounded-lg bg-yellow-50 p-3 text-sm">
                      <X className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-600" />
                      <div>
                        <p className="font-medium text-yellow-900">信頼度が低いです</p>
                        <p className="mt-1 text-xs text-yellow-700">
                          画像の品質を確認し、必要に応じて手動で修正してください
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <FileText className="h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-sm text-muted-foreground">
                    画像をアップロードしてOCRを実行してください
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
