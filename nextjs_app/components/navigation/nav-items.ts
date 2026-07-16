import {
  FileText,
  Play,
  BarChart3,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  matchPaths: string[];
}

export const NAV_ITEMS: NavItem[] = [
  {
    label: "Quellen",
    href: "/quellen",
    icon: FileText,
    matchPaths: ["/quellen", "/entwuerfe"],
  },
  {
    label: "Backtests",
    href: "/batches",
    icon: Play,
    matchPaths: ["/batches"],
  },
  {
    label: "Ergebnisse",
    href: "/ergebnisse",
    icon: BarChart3,
    matchPaths: ["/ergebnisse", "/runs"],
  },
  {
    label: "Einstellungen",
    href: "/einstellungen",
    icon: Settings,
    matchPaths: ["/einstellungen"],
  },
];

export function findActiveItem(pathname: string): NavItem | undefined {
  return NAV_ITEMS.find((item) =>
    item.matchPaths.some((p) => pathname === p || pathname.startsWith(p + "/")),
  );
}
