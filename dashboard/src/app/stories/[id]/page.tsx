import { createClient } from "@/lib/supabase/server";
import { Story } from "@/types";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Button } from "@/components/ui/button";

interface StoryDetailsPageProps {
  params: {
    id: string;
  };
}

// TODO: This should be a more complete type
type StoryDetails = Story & { description?: string };

export default async function StoryDetailsPage({ params }: StoryDetailsPageProps) {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("stories")
    .select("*")
    .eq("id", params.id)
    .single();

  if (error || !data) {
    notFound();
  }
  
  const story: StoryDetails = data;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
         <h1 className="text-2xl font-bold">Story: {story.topic}</h1>
         {story.status === 'ready_for_review' && (
           <Button asChild>
              <Link href={`/stories/${story.id}/review`}>Review Video</Link>
           </Button>
         )}
      </div>

      <p>Status: {story.status}</p>
      <p>Description: {story.description || 'Not available'}</p>
      
      {/* TODO: Create a client component to show real-time progress of scenes */}
      <h2 className="mt-4 text-xl font-bold">Scene Progress</h2>
      <p>Placeholder for scene status list.</p>
    </div>
  );
}
