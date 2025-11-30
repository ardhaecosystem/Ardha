"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";

export function Breadcrumbs() {
  const pathname = usePathname();

  // Generate breadcrumbs from pathname
  const segments = pathname.split("/").filter(Boolean);

  // Don't show breadcrumbs on root pages
  if (segments.length <= 1) {
    return null;
  }

  // Build breadcrumb items
  const breadcrumbs = segments.map((segment, index) => {
    const href = "/" + segments.slice(0, index + 1).join("/");
    const label = segment
      .split("-")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");

    return { href, label, isLast: index === segments.length - 1 };
  });

  return (
    <div className="flex items-center gap-2 px-6 py-3 bg-black/30 border-b border-white/10">
      {/* Home */}
      <Link
        href="/dashboard"
        className="text-white/60 hover:text-white transition-colors duration-200"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
          />
        </svg>
      </Link>

      {/* Breadcrumb trail */}
      {breadcrumbs.map((crumb) => (
        <div key={crumb.href} className="flex items-center gap-2">
          {/* Separator */}
          <svg
            className="w-4 h-4 text-white/40"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>

          {/* Crumb */}
          {crumb.isLast ? (
            <span className="text-white font-medium">{crumb.label}</span>
          ) : (
            <Link
              href={crumb.href}
              className="text-white/60 hover:text-white transition-colors duration-200"
            >
              {crumb.label}
            </Link>
          )}
        </div>
      ))}
    </div>
  );
}
