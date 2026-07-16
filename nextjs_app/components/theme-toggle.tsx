"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }) {
  const [dark, setDark] = useState(true);

  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);

  function toggleTheme() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.theme = next ? "dark" : "light";
    setDark(next);
  }

  const defaultClasses = "fixed right-4 top-4 z-50";

  return (
    <Button
      className={cn(!className ? defaultClasses : "", className)}
      variant="outline"
      size="icon"
      onClick={toggleTheme}
      aria-label={dark ? "Helles Design aktivieren" : "Dunkles Design aktivieren"}
    >
      {dark ? <Sun /> : <Moon />}
    </Button>
  );
}
