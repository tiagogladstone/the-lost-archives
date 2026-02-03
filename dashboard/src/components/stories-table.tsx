'use client';

import { useEffect, useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { createClient } from '@/lib/supabase/client';
import { Story } from '@/types';

interface StoriesTableProps {
  initialStories: Story[];
}

const statusColors: { [key: string]: 'default' | 'secondary' | 'destructive' | 'outline' } = {
  pending: 'secondary',
  generating_script: 'default',
  producing: 'default',
  rendering: 'default',
  ready_for_review: 'default',
  published: 'default',
  failed: 'destructive',
};

const StatusBadge = ({ status }: { status: string }) => {
  const [pulsate, setPulsate] = useState(false);

  useEffect(() => {
    if (status === 'ready_for_review') {
      setPulsate(true);
    } else {
      setPulsate(false);
    }
  }, [status]);

  const colorClass = 
    status === 'generating_script' ? 'bg-blue-500' :
    status === 'producing' ? 'bg-yellow-500' :
    status === 'rendering' ? 'bg-orange-500' :
    status === 'ready_for_review' ? 'bg-green-500' :
    status === 'published' ? 'bg-green-700' :
    '';

  return (
    <Badge variant={statusColors[status] || 'secondary'} className={`${colorClass} ${pulsate ? 'animate-pulse' : ''}`}>
      {status.replace(/_/g, ' ')}
    </Badge>
  );
};

export function StoriesTable({ initialStories }: StoriesTableProps) {
  const [stories, setStories] = useState(initialStories);
  const supabase = createClient();

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
          const newStory = payload.new as Story;
          setStories((currentStories) => {
            // Check if the story is new or an update
            const storyExists = currentStories.some((story) => story.id === newStory.id);
            if (storyExists) {
              // Update existing story
              return currentStories.map((story) =>
                story.id === newStory.id ? newStory : story
              );
            } else {
              // Add new story to the top
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
              <TableRow key={story.id}>
                <TableCell className="font-medium">{story.topic}</TableCell>
                <TableCell>
                  <StatusBadge status={story.status} />
                </TableCell>
                <TableCell>{story.target_duration_minutes}</TableCell>
                <TableCell>{new Date(story.created_at).toLocaleString()}</TableCell>
                <TableCell>{/* TODO: Add actions button */}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
