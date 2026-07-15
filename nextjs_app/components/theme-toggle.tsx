"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const [dark, setDark] = useState(true);

  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);

  function toggleTheme() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.theme = next ? "dark" : "light";
    setDark(next);
  }

  return (
    <Button className="fixed right-4 top-4 z-50" variant="outline" size="icon" onClick={toggleTheme} aria-label={dark ? "Helles Design aktivieren" : "Dunkles Design aktivieren"}>
      {dark ? <Sun /> : <Moon />}
    </Button>
  );
}
