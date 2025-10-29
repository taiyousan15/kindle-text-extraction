"use client";

import { Bell, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { useQuery } from "react-query";
import { api } from "@/lib/api";

export function Header() {
  const { theme, setTheme } = useTheme();

  const { data: health } = useQuery("health", api.health, {
    refetchInterval: 30000,
  });

  return (
    <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-white px-6 dark:bg-gray-900">
      <div className="flex items-center space-x-4">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          書籍OCR & RAGシステム
        </h1>
      </div>

      <div className="flex items-center space-x-4">
        {/* Health Status */}
        {health && (
          <div className="flex items-center space-x-2 text-sm">
            <div
              className={`h-2 w-2 rounded-full ${
                health.status === "healthy" ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="text-gray-600 dark:text-gray-400">
              {health.status === "healthy" ? "正常" : "異常"}
            </span>
          </div>
        )}

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">テーマ切り替え</span>
        </Button>

        {/* Notifications */}
        <Button variant="ghost" size="icon">
          <Bell className="h-5 w-5" />
          <span className="sr-only">通知</span>
        </Button>
      </div>
    </header>
  );
}
