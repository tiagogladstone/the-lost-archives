"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiGet, apiDelete } from "@/lib/api";
import { StoryDetail, StoryStatus } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ArrowLeft,
  Trash2,
  Eye,
  ExternalLink,
  AlertCircle,
  Loader2,
  Clock,
  Film,
  Globe,
  Palette,
  Monitor,
  Calendar,
  Image as ImageIcon,
} from "lucide-react";

const STATUS_PROGRESS: Record<StoryStatus, number> = {
  draft: 0,
  scripting: 15,
  producing: 40,
  rendering: 60,
  post_production: 80,
  ready_for_review: 100,
  publishing: 100,
  published: 100,
  failed: 0, // handled separately
};

const STATUS_COLORS: Record<StoryStatus, string> = {
  draft: "bg-zinc-500",
  scripting: "bg-blue-500",
  producing: "bg-yellow-500",
  rendering: "bg-orange-500",
  post_production: "bg-purple-500",
  ready_for_review: "bg-green-500",
  publishing: "bg-blue-500",
  published: "bg-green-700",
  failed: "bg-red-500",
};

const PROGRESS_BAR_COLORS: Record<StoryStatus, string> = {
  draft: "bg-zinc-500",
  scripting: "bg-blue-500",
  producing: "bg-yellow-500",
  rendering: "bg-orange-500",
  post_production: "bg-purple-500",
  ready_for_review: "bg-green-500",
  publishing: "bg-green-500",
  published: "bg-green-700",
  failed: "bg-red-500",
};

// Statuses that are "in progress" and should trigger polling
const IN_PROGRESS_STATUSES: StoryStatus[] = [
  "scripting",
  "producing",
  "rendering",
  "post_production",
  "publishing",
];

function getProgressForStatus(status: StoryStatus): number {
  if (status === "failed") {
    // For failed, we don't know where it failed, show 0
    return 0;
  }
  return STATUS_PROGRESS[status];
}

function StatusBadge({ status }: { status: StoryStatus }) {
  const isPulsing = status === "ready_for_review";
  const isInProgress = IN_PROGRESS_STATUSES.includes(status);

  return (
    <Badge
      variant={status === "failed" ? "destructive" : "secondary"}
      className={`${STATUS_COLORS[status]} text-white ${isPulsing ? "animate-pulse" : ""} ${isInProgress ? "animate-pulse" : ""}`}
    >
      {status.replace(/_/g, " ")}
    </Badge>
  );
}

export default function StoryDetailsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [story, setStory] = useState<StoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchStory = useCallback(async () => {
    try {
      const data = await apiGet<StoryDetail>(`/stories/${params.id}`);
      setStory(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch story");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  // Initial fetch
  useEffect(() => {
    fetchStory();
  }, [fetchStory]);

  // Polling for in-progress statuses
  useEffect(() => {
    if (!story) return;
    if (!IN_PROGRESS_STATUSES.includes(story.status)) return;

    const interval = setInterval(() => {
      fetchStory();
    }, 5000);

    return () => clearInterval(interval);
  }, [story, fetchStory]);

  async function handleDelete() {
    if (!story) return;
    if (!window.confirm(`Are you sure you want to delete "${story.topic}"?`)) return;

    setDeleting(true);
    try {
      await apiDelete(`/stories/${story.id}`);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete story");
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !story) {
    return (
      <div className="flex flex-col items-center gap-4 py-20">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-lg text-destructive">{error}</p>
        <Button variant="outline" asChild>
          <Link href="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Stories
          </Link>
        </Button>
      </div>
    );
  }

  if (!story) return null;

  const progress = getProgressForStatus(story.status);

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div className="flex flex-1 items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{story.topic}</h1>
            <StatusBadge status={story.status} />
          </div>
          <div className="flex items-center gap-2">
            {story.status === "ready_for_review" && (
              <Button asChild>
                <Link href={`/stories/${story.id}/review`}>
                  <Eye className="mr-2 h-4 w-4" />
                  Review
                </Link>
              </Button>
            )}
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete
            </Button>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {story.error_message && (
        <Card className="border-destructive">
          <CardContent className="flex items-start gap-3 pt-6">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Pipeline Error</p>
              <p className="text-sm text-muted-foreground">{story.error_message}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Progress Bar */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <div className="h-3 flex-1 overflow-hidden rounded-full bg-secondary">
              <div
                className={`h-full rounded-full transition-all duration-500 ${PROGRESS_BAR_COLORS[story.status]}`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-sm font-medium text-muted-foreground">
              {progress}%
            </span>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {story.status === "failed"
              ? "Pipeline failed. Check the error above."
              : story.status === "published"
                ? "Video published successfully."
                : story.status === "ready_for_review"
                  ? "Ready for review. Select title and thumbnail."
                  : `Currently: ${story.status.replace(/_/g, " ")}...`}
          </p>
        </CardContent>
      </Card>

      {/* Info Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {story.description && (
          <Card className="sm:col-span-2 lg:col-span-3">
            <CardHeader className="pb-2">
              <CardDescription>Description</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm">{story.description}</p>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Palette className="h-3.5 w-3.5" /> Style
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm font-medium capitalize">{story.style}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Monitor className="h-3.5 w-3.5" /> Aspect Ratio
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm font-medium">{story.aspect_ratio}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Globe className="h-3.5 w-3.5" /> Languages
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm font-medium">
              {story.languages?.length ? story.languages.join(", ") : "N/A"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" /> Duration
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm font-medium">
              {story.target_duration_minutes} min
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5" /> Created
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm font-medium">
              {new Date(story.created_at).toLocaleString()}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Video Player */}
      {story.video_url && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Film className="h-5 w-5" /> Video
            </CardTitle>
          </CardHeader>
          <CardContent>
            <video
              src={story.video_url}
              controls
              className="w-full max-w-2xl rounded-lg"
            >
              Your browser does not support the video tag.
            </video>
          </CardContent>
        </Card>
      )}

      {/* YouTube Link */}
      {story.youtube_url && (
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <ExternalLink className="h-5 w-5 text-red-500" />
            <a
              href={story.youtube_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-red-500 underline underline-offset-2 hover:text-red-400"
            >
              Watch on YouTube
            </a>
          </CardContent>
        </Card>
      )}

      {/* Scenes */}
      {story.scenes && story.scenes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Scenes ({story.scenes.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">#</TableHead>
                  <TableHead className="w-20">Image</TableHead>
                  <TableHead>Text</TableHead>
                  <TableHead className="w-24">Duration</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {story.scenes
                  .sort((a, b) => a.scene_order - b.scene_order)
                  .map((scene) => (
                    <TableRow key={scene.id}>
                      <TableCell className="font-mono text-muted-foreground">
                        {scene.scene_order}
                      </TableCell>
                      <TableCell>
                        {scene.image_url ? (
                          <img
                            src={scene.image_url}
                            alt={`Scene ${scene.scene_order}`}
                            className="h-12 w-12 rounded object-cover"
                          />
                        ) : (
                          <div className="flex h-12 w-12 items-center justify-center rounded bg-muted">
                            <ImageIcon className="h-4 w-4 text-muted-foreground" />
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="max-w-md">
                        <p className="truncate text-sm">
                          {scene.text_content.length > 150
                            ? `${scene.text_content.slice(0, 150)}...`
                            : scene.text_content}
                        </p>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {scene.duration_seconds
                          ? `${scene.duration_seconds.toFixed(1)}s`
                          : "--"}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
