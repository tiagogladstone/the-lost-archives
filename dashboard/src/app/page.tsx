import { createClient } from "@/lib/supabase/server";
import { PlusCircle } from "lucide-react";

// TODO: Move to a types file
export type Story = {
  id: string;
  topic: string;
  status: string;
  target_duration_minutes: number;
  created_at: string;
};

export default async function DashboardPage() {
  const supabase = createClient();
  const { data: stories, error } = await supabase
    .from("stories")
    .select("id, topic, status, target_duration_minutes, created_at")
    .order("created_at", { ascending: false });
    
  if (error) {
    console.error("Error fetching stories:", error);
    // TODO: Handle error state in the UI
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Stories</h1>
        {/* TODO: Add Link to /new */}
        <button className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
          <PlusCircle className="h-4 w-4" />
          New Story
        </button>
      </div>
      
      {/* TODO: Pass stories to a client component table with Realtime */}
      <pre>{JSON.stringify(stories, null, 2)}</pre>
    </div>
  );
}
