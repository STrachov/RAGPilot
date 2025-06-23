"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { adminService } from "@/services/admin";

const StatCard = ({ 
  title, 
  value, 
  unit, 
  icon, 
  color = "blue" 
}: {
  title: string;
  value: number;
  unit?: string;
  icon: React.ReactNode;
  color?: "blue" | "green" | "purple" | "orange";
}) => {
  const colorClasses = {
    blue: "bg-blue-500",
    green: "bg-green-500", 
    purple: "bg-purple-500",
    orange: "bg-orange-500",
  };

  return (
    <div className="rounded-sm border border-stroke bg-white p-6 shadow-default dark:border-strokedark dark:bg-boxdark">
      <div className="flex h-11.5 w-11.5 items-center justify-center rounded-full bg-meta-2 dark:bg-meta-4">
        <div className={`flex h-8 w-8 items-center justify-center rounded-full ${colorClasses[color]} text-white`}>
          {icon}
        </div>
      </div>

      <div className="mt-4 flex items-end justify-between">
        <div>
          <h4 className="text-title-md font-bold text-black dark:text-white">
            {value.toLocaleString()}{unit && <span className="text-sm text-meta-3">{unit}</span>}
          </h4>
          <span className="text-sm font-medium text-meta-3">{title}</span>
        </div>
      </div>
    </div>
  );
};

export const SystemStatsCard = () => {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['systemStats'],
    queryFn: adminService.getSystemStats,
    //refetchInterval: 60000, // Refresh every 60 seconds - less critical than document status
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-4 2xl:gap-7.5">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="animate-pulse rounded-sm border border-stroke bg-white p-6 shadow-default dark:border-strokedark dark:bg-boxdark">
            <div className="h-20 bg-gray-200 rounded dark:bg-gray-700"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-sm border border-stroke bg-white p-6 shadow-default dark:border-strokedark dark:bg-boxdark">
        <div className="text-center text-red-500">
          Failed to load system statistics
        </div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-3 2xl:gap-7.5">
      <StatCard
        title="Total Documents"
        value={stats.total_documents}
        icon={
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
          </svg>
        }
        color="blue"
      />

      {/* <StatCard
        title="Text Chunks"
        value={stats.total_chunks}
        icon={
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        }
        color="green"
      /> */}
      <StatCard
        title="Storage Used"
        value={stats.storage_used_mb}
        unit="MB"
        icon={
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        }
        color="green"
      />

      {/* <StatCard
        title="Total Queries"
        value={stats.total_queries}
        icon={
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
          </svg>
        }
        color="purple"
      /> */}

      <StatCard
        title="Active Users"
        value={stats.active_users}
        icon={
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
          </svg>
        }
        color="orange"
      />
    </div>
  );
}; 