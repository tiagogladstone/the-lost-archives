"use client";

import { useEffect, useState } from "react";
import { PlusCircle } from "lucide-react";
import { StoriesTable } from "@/components/stories-table";
import { Story } from "@/types";
import { Button } from "@/components/ui/button";
import { apiGet } from "@/lib/api";
import Link from "next/link";

export default function DashboardPage() {
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet<Story[]>("/stories")
      .then(setStories)
      .catch((err) => console.error("Error fetching stories:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Stories</h1>
        <Button asChild>
          <Link href="/new">
            <PlusCircle className="mr-2 h-4 w-4" />
            New Story
          </Link>
        </Button>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Loading stories...</p>
      ) : (
        <StoriesTable initialStories={stories} />
      )}
    </div>
  );
}
