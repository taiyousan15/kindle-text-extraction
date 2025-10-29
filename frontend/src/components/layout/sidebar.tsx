"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Home,
  Upload,
  Camera,
  List,
  MessageSquare,
  BookOpen,
  Settings,
} from "lucide-react";

const navigation = [
  { name: "ダッシュボード", href: "/", icon: Home },
  { name: "OCRアップロード", href: "/upload", icon: Upload },
  { name: "自動キャプチャ", href: "/capture", icon: Camera },
  { name: "ジョブ管理", href: "/jobs", icon: List },
  { name: "RAG検索", href: "/rag", icon: MessageSquare },
  { name: "ナレッジベース", href: "/knowledge", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-64 flex-col bg-gray-900 text-white">
      {/* Logo */}
      <div className="flex h-16 items-center justify-center border-b border-gray-800">
        <div className="flex items-center space-x-2">
          <BookOpen className="h-8 w-8 text-blue-400" />
          <span className="text-xl font-bold">Kindle OCR</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-gray-800 text-white"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white"
              )}
            >
              <item.icon
                className={cn(
                  "mr-3 h-5 w-5 flex-shrink-0",
                  isActive ? "text-blue-400" : "text-gray-400 group-hover:text-gray-300"
                )}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-800 p-4">
        <Link
          href="/settings"
          className="group flex items-center rounded-md px-3 py-2 text-sm font-medium text-gray-300 transition-colors hover:bg-gray-800 hover:text-white"
        >
          <Settings className="mr-3 h-5 w-5 flex-shrink-0 text-gray-400 group-hover:text-gray-300" />
          設定
        </Link>
        <div className="mt-4 text-xs text-gray-500">
          <p>Kindle OCR v2.0.0</p>
          <p className="mt-1">Powered by Next.js & FastAPI</p>
        </div>
      </div>
    </div>
  );
}
