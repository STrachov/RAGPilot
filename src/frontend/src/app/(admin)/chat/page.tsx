"use client";

import React, { useEffect } from "react";
import { ChatIcon } from "@/icons/index";

export default function ChatPage() {
  useEffect(() => {
    document.title = "Chat & Query | RAGPilot";
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Chat & Query
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Ask questions about your documents using AI
          </p>
        </div>
      </div>

      {/* Chat Interface Placeholder */}
      <div className="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <ChatIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
              Chat Interface
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Coming soon - Interactive AI assistant for document Q&A
            </p>
            <div className="mt-4">
              <p className="text-xs text-gray-400">
                Features will include:
              </p>
              <ul className="mt-2 text-xs text-gray-500 space-y-1">
                <li>• Real-time streaming responses</li>
                <li>• Source document citations</li>
                <li>• Query history and suggestions</li>
                <li>• Multi-document reasoning</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 