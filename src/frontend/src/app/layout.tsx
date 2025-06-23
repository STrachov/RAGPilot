'use client';

import { Outfit } from 'next/font/google';
import './globals.css';

import { SidebarProvider } from '@/context/SidebarContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { QueryProvider } from '@/providers/QueryProvider';
import { useAuthStore } from '@/stores/authStore';
import { useEffect } from 'react';

const outfit = Outfit({
  subsets: ["latin"],
});

function AuthInitializer({ children }: { children: React.ReactNode }) {
  const { checkAuth } = useAuthStore();

  // Initialize auth state on app startup
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return <>{children}</>;
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${outfit.className} dark:bg-gray-900`}>
        <QueryProvider>
          <ThemeProvider>
            <AuthInitializer>
              <SidebarProvider>{children}</SidebarProvider>
            </AuthInitializer>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
