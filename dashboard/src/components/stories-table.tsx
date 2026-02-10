'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { createClient } from '@/lib/supabase/client';
import { Story, StoryStatus } from '@/types';
import { apiDelete } from '@/lib/api';
import { Eye, Trash2, Loader2 } from 'lucide-react';

interface StoriesTableProps {
  initialStories: Story[];
}

const STATUS_COLORS: Record<StoryStatus, string> = {
  draft: 'bg-zinc-500',
  scripting: 'bg-blue-500',
  producing: 'bg-yellow-500',
  rendering: 'bg-orange-500',
  post_production: 'bg-purple-500',
  ready_for_review: 'bg-green-500',
  publishing: 'bg-blue-500',
  published: 'bg-green-700',
  failed: 'bg-red-500',
};

const StatusBadge = ({ status }: { status: StoryStatus }) => {
  const isPulsing = status === 'ready_for_review';

  return (
    <Badge
      variant={status === 'failed' ? 'destructive' : 'secondary'}
      className={`${STATUS_COLORS[status] || ''} text-white ${isPulsing ? 'animate-pulse' : ''}`}
    >
      {status.replace(/_/g, ' ')}
    </Badge>
  );
};

export function StoriesTable({ initialStories }: StoriesTableProps) {
  const [stories, setStories] = useState(initialStories);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const supabase = createClient();
  const router = useRouter();

  useEffect(() => {
    setStories(initialStories);
  }, [initialStories]);

  useEffect(() => {
    const channel = supabase
      .channel('stories-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'stories' },
        (payload) => {
          console.log('Change received!', payload);
          if (payload.eventType === 'DELETE') {
            const oldStory = payload.old as { id: string };
            setStories((current) => current.filter((s) => s.id !== oldStory.id));
            return;
          }
          const newStory = payload.new as Story;
          setStories((currentStories) => {
            const storyExists = currentStories.some((story) => story.id === newStory.id);
            if (storyExists) {
              return currentStories.map((story) =>
                story.id === newStory.id ? newStory : story
              );
            } else {
              return [newStory, ...currentStories];
            }
          });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [supabase]);

  async function handleDelete(e: React.MouseEvent, storyId: string, topic: string) {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete "${topic}"?`)) return;

    setDeletingId(storyId);
    try {
      await apiDelete(`/stories/${storyId}`);
      setStories((current) => current.filter((s) => s.id !== storyId));
    } catch (err) {
      console.error('Failed to delete story:', err);
    } finally {
      setDeletingId(null);
    }
  }

  function handleRowClick(storyId: string) {
    router.push(`/stories/${storyId}`);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>All Stories</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Topic</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Duration (min)</TableHead>
              <TableHead>Created At</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stories.map((story) => (
              <TableRow
                key={story.id}
                className="cursor-pointer"
                onClick={() => handleRowClick(story.id)}
              >
                <TableCell className="font-medium">{story.topic}</TableCell>
                <TableCell>
                  <StatusBadge status={story.status} />
                </TableCell>
                <TableCell>{(story as Story & { target_duration_minutes?: number }).target_duration_minutes ?? '--'}</TableCell>
                <TableCell>{new Date(story.created_at).toLocaleString()}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      onClick={() => handleRowClick(story.id)}
                      title="View details"
                    >
                      <Eye className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      onClick={(e) => handleDelete(e, story.id, story.topic)}
                      disabled={deletingId === story.id}
                      title="Delete story"
                      className="text-destructive hover:text-destructive"
                    >
                      {deletingId === story.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
