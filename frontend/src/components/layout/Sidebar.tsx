import { useState, useEffect, useRef, useCallback } from "react";
import { Menu } from "lucide-react";
import { cn } from "../../lib/utils";
import { Separator } from "../ui/separator";
import { NotificationBell } from "../notifications/NotificationBell";
import { SidebarHeader } from "./SidebarHeader";
import { SidebarUserMenu } from "./SidebarUserMenu";
import { SidebarNav } from "./SidebarNav";
import { SidebarToggle } from "./SidebarToggle";

interface SidebarProps {
  children: React.ReactNode;
}

export function Sidebar({ children }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const stored = localStorage.getItem("sidebar-collapsed");
    // Default to collapsed if no preference stored
    return stored !== "false";
  });
  const [isPeeking, setIsPeeking] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const enterTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const leaveTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up timeouts on unmount
  useEffect(() => {
    return () => {
      if (enterTimeout.current) clearTimeout(enterTimeout.current);
      if (leaveTimeout.current) clearTimeout(leaveTimeout.current);
    };
  }, []);

  const handleToggle = useCallback(() => {
    setIsCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed", String(next));
      // Clear peek when toggling
      setIsPeeking(false);
      return next;
    });
  }, []);

  const handleMouseEnter = useCallback(() => {
    if (!isCollapsed) return;
    if (leaveTimeout.current) {
      clearTimeout(leaveTimeout.current);
      leaveTimeout.current = null;
    }
    enterTimeout.current = setTimeout(() => {
      setIsPeeking(true);
    }, 150);
  }, [isCollapsed]);

  const handleMouseLeave = useCallback(() => {
    if (enterTimeout.current) {
      clearTimeout(enterTimeout.current);
      enterTimeout.current = null;
    }
    leaveTimeout.current = setTimeout(() => {
      setIsPeeking(false);
    }, 300);
  }, []);

  const closeMobile = useCallback(() => setIsMobileOpen(false), []);

  const effectiveExpanded = !isCollapsed || isPeeking;
  const width = effectiveExpanded ? 240 : 56;

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden md:flex fixed left-0 top-0 h-screen z-40 flex-col bg-secondary border-r border-border transition-all duration-200 ease-in-out",
          isPeeking && "shadow-[4px_0_12px_rgba(0,0,0,0.08)]"
        )}
        style={{ width: `${width}px` }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <SidebarHeader isCollapsed={!effectiveExpanded} />
        <SidebarUserMenu isCollapsed={!effectiveExpanded} />
        <div className={cn("flex items-center shrink-0 pb-1", effectiveExpanded ? "px-3" : "justify-center")}>
          <NotificationBell isCollapsed={!effectiveExpanded} />
        </div>
        <Separator />
        <SidebarNav isCollapsed={!effectiveExpanded} />
        <div className="flex-1" />
        <SidebarToggle isCollapsed={isCollapsed} onToggle={handleToggle} />
      </aside>

      {/* Desktop main content */}
      <main
        className="hidden md:block transition-all duration-200 ease-in-out min-h-screen"
        style={{ marginLeft: `${isPeeking ? 56 : width}px` }}
      >
        {children}
      </main>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-12 bg-secondary border-b border-border z-40 flex items-center px-4">
        <button
          onClick={() => setIsMobileOpen((prev) => !prev)}
          className="p-1 hover:bg-accent rounded-md transition-colors"
        >
          <Menu className="size-6" />
        </button>
        <span className="flex-1 text-center text-base font-semibold">
          Documentum
        </span>
        <NotificationBell />
      </div>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 bg-black/20 z-40"
            onClick={closeMobile}
          />
          <aside className="md:hidden fixed left-0 top-0 h-screen w-60 bg-secondary z-50 flex flex-col">
            <SidebarHeader isCollapsed={false} />
            <SidebarUserMenu isCollapsed={false} />
            <Separator />
            <SidebarNav isCollapsed={false} onNavClick={closeMobile} />
          </aside>
        </>
      )}

      {/* Mobile main content */}
      <main className="md:hidden pt-12 min-h-screen">{children}</main>
    </>
  );
}
