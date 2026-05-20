import { FileSearch, Eraser, MessageSquareText, FolderOpen, Menu, X, ChevronDown } from "lucide-react";
import { useState } from "react";
import type { AppMode } from "../types";

type TopNavigationProps = {
  currentMode: AppMode | "WORKSPACE";
  onModeChange: (mode: AppMode | "WORKSPACE") => void;
};

const navItems: Array<{
  value: AppMode | "WORKSPACE";
  label: string;
  icon: React.ElementType;
}> = [
  { value: "WORKSPACE", label: "Workspace", icon: FolderOpen },
  { value: "AUDIT", label: "Audit", icon: FileSearch },
  { value: "REDACTION", label: "Redaction", icon: Eraser },
  { value: "ADVISORY", label: "Advisory", icon: MessageSquareText },
];

export function TopNavigation({ currentMode, onModeChange }: TopNavigationProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [desktopDropdownOpen, setDesktopDropdownOpen] = useState(false);

  const currentItem = navItems.find((item) => item.value === currentMode) || navItems[0];
  const CurrentIcon = currentItem.icon;

  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-900">Zynexra</span>
            <span className="hidden sm:inline text-slate-400">/</span>
            <button
              onClick={() => onModeChange("WORKSPACE")}
              className={`hidden sm:flex items-center gap-1.5 px-2 py-1 text-sm font-medium rounded-md transition-colors ${
                currentMode === "WORKSPACE"
                  ? "bg-blue-100 text-blue-900"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <FolderOpen className="h-4 w-4" />
              Workspace
            </button>
          </div>

          <div className="flex items-center gap-1 lg:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-700 rounded-md hover:bg-slate-100"
            >
              <CurrentIcon className="h-4 w-4" />
              <span className="text-slate-500">{currentItem.label}</span>
              {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>

          <div className="hidden lg:flex items-center gap-1">
            {navItems.slice(1).map((item) => {
              const Icon = item.icon;
              const isActive = currentMode === item.value;
              return (
                <button
                  key={item.value}
                  onClick={() => onModeChange(item.value as AppMode)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </div>

          <div className="hidden lg:flex relative">
            <button
              onClick={() => setDesktopDropdownOpen(!desktopDropdownOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-600 rounded-md hover:bg-slate-100"
            >
              <CurrentIcon className="h-4 w-4" />
              {currentItem.label}
              <ChevronDown className="h-3 w-3" />
            </button>
            {desktopDropdownOpen && (
              <div className="absolute right-0 top-full mt-1 w-40 rounded-md border border-slate-200 bg-white py-1 shadow-lg">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = currentMode === item.value;
                  return (
                    <button
                      key={item.value}
                      onClick={() => {
                        onModeChange(item.value);
                        setDesktopDropdownOpen(false);
                      }}
                      className={`flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors ${
                        isActive
                          ? "bg-blue-50 text-blue-900 font-medium"
                          : "text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-200 px-4 py-3">
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentMode === item.value;
              return (
                <button
                  key={item.value}
                  onClick={() => {
                    onModeChange(item.value);
                    setMobileMenuOpen(false);
                  }}
                  className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-100 text-blue-900"
                      : "text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </nav>
  );
}