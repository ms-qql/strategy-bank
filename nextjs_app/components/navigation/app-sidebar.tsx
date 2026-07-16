"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import packageJson from "@/package.json";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { NAV_ITEMS, findActiveItem } from "./nav-items";

export function AppSidebar() {
  const pathname = usePathname();
  const activeItem = findActiveItem(pathname);

  return (
    <Sidebar collapsible="icon" className="border-r border-sidebar-border">
      <SidebarHeader className="gap-0 px-4 pt-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">
            Strategy Bank
          </span>
          <span className="font-mono text-[10px] tracking-wider text-muted-foreground">
            v{packageJson.version}
          </span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive =
                  activeItem?.href === item.href;

                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      isActive={isActive}
                      tooltip={item.label}
                      render={<Link href={item.href} prefetch />}
                    >
                      <Icon />
                      <span>{item.label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="gap-2 px-4 pb-2">
        <ThemeToggle className="w-full" />
      </SidebarFooter>
    </Sidebar>
  );
}
