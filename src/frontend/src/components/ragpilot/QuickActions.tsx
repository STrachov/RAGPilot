"use client";

import React from "react";
import Link from "next/link";

const ActionCard = ({
  title,
  description,
  icon,
  href,
  onClick,
  color = "blue"
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  href?: string;
  onClick?: () => void;
  color?: "blue" | "green" | "purple" | "orange";
}) => {
  const colorClasses = {
    blue: "border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 dark:border-blue-700 dark:bg-blue-900/20 dark:hover:bg-blue-900/30 dark:text-blue-400",
    green: "border-green-200 bg-green-50 hover:bg-green-100 text-green-700 dark:border-green-700 dark:bg-green-900/20 dark:hover:bg-green-900/30 dark:text-green-400",
    purple: "border-purple-200 bg-purple-50 hover:bg-purple-100 text-purple-700 dark:border-purple-700 dark:bg-purple-900/20 dark:hover:bg-purple-900/30 dark:text-purple-400",
    orange: "border-orange-200 bg-orange-50 hover:bg-orange-100 text-orange-700 dark:border-orange-700 dark:bg-orange-900/20 dark:hover:bg-orange-900/30 dark:text-orange-400",
  };

  const content = (
    <div className="flex items-start space-x-3">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/50">
        {icon}
      </div>
      <div>
        <h3 className="font-medium">{title}</h3>
        <p className="text-sm opacity-70">{description}</p>
      </div>
    </div>
  );

  if (onClick) {
    return (
      <button
        onClick={onClick}
        className={`block w-full text-left rounded-lg border p-4 transition-colors ${colorClasses[color]}`}
      >
        {content}
      </button>
    );
  }

  return (
    <Link
      href={href!}
      className={`block rounded-lg border p-4 transition-colors ${colorClasses[color]}`}
    >
      {content}
    </Link>
  );
};

export const QuickActions = ({ onUploadClick }: { onUploadClick?: () => void }) => {
  return (
    <div className="rounded-sm border border-stroke bg-white p-6 shadow-default dark:border-strokedark dark:bg-boxdark">
      <div className="mb-6">
        <h4 className="text-xl font-semibold text-black dark:text-white">
          Quick Actions
        </h4>
      </div>

      <div className="space-y-4">
        <ActionCard
          title="Upload Documents"
          description="Add new documents to the knowledge base"
          icon={
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          }
          color="blue"
          onClick={onUploadClick}
        />

        <ActionCard
          title="View Documents"
          description="Manage your document library"
          href="/documents"
          icon={
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
          color="green"
        />

        <ActionCard
          title="Configure Pipeline"
          description="Adjust chunking, embeddings, and retrieval"
          href="/admin/config"
          icon={
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
            </svg>
          }
          color="purple"
        />

        <ActionCard
          title="User Management"
          description="Manage users and permissions"
          href="/admin/users"
          icon={
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
            </svg>
          }
          color="orange"
        />
      </div>

      <div className="mt-6 pt-6 border-t border-stroke dark:border-strokedark">
        <div className="text-center">
          <p className="text-sm text-meta-3 mb-3">Need help?</p>
          <Link 
            href="/help" 
            className="inline-flex items-center text-sm text-primary hover:underline"
          >
            View Documentation
            <svg className="ml-1 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </Link>
        </div>
      </div>
    </div>
  );
}; 