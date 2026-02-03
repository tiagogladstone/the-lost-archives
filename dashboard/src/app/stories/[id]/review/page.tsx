'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Story } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';

interface TitleOption {
  id: string;
  title_text: string;
  story_id: string;
}

interface ThumbnailOption {
  id: string;
  image_url: string;
  story_id: string;
  feedback_history: any[];
  version: number;
}

export default function ReviewPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const supabase = createClient();
  const { id } = params;

  const [story, setStory] = useState<Story | null>(null);
  const [titles, setTitles] = useState<TitleOption[]>([]);
  const [thumbnails, setThumbnails] = useState<ThumbnailOption[]>([]);
  
  const [selectedTitleId, setSelectedTitleId] = useState<string>('');
  const [selectedThumbId, setSelectedThumbId] = useState<string>('');
  const [thumbFeedback, setThumbFeedback] = useState<Record<string, string>>({});
  
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [publishing, setPublishing] = useState(false);
  const [videoUrl, setVideoUrl] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        
        // 1. Fetch Story
        const { data: storyData, error: storyError } = await supabase
          .from('stories')
          .select('*')
          .eq('id', id)
          .single();
        
        if (storyError) throw storyError;
        setStory(storyData);
        setDescription(storyData.description || ''); // Pre-fill if available (though type might not have it yet based on index.ts read, but DB likely does)

        // 2. Fetch Titles
        const { data: titleData, error: titleError } = await supabase
          .from('title_options')
          .select('*')
          .eq('story_id', id);
          
        if (titleError) console.error('Error fetching titles:', titleError);
        else setTitles(titleData || []);

        // 3. Fetch Thumbnails
        const { data: thumbData, error: thumbError } = await supabase
          .from('thumbnail_options')
          .select('*')
          .eq('story_id', id)
          .order('version', { ascending: false });

        if (thumbError) console.error('Error fetching thumbnails:', thumbError);
        else setThumbnails(thumbData || []);

        // 4. Get Video Signed URL
        const { data: videoData, error: videoError } = await supabase
          .storage
          .from('videos')
          .createSignedUrl(`${id}/final_video.mp4`, 3600); // 1 hour expiry

        if (videoError) console.error('Error fetching video URL:', videoError);
        else if (videoData) setVideoUrl(videoData.signedUrl);

      } catch (err) {
        console.error('Failed to load review data:', err);
      } finally {
        setLoading(false);
      }
    }

    if (id) {
      loadData();
    }
  }, [id, supabase]);

  const handlePublish = async () => {
    if (!story || !selectedTitleId || !selectedThumbId) return;

    try {
      setPublishing(true);

      const selectedTitle = titles.find(t => t.id === selectedTitleId);
      const selectedThumb = thumbnails.find(t => t.id === selectedThumbId);

      // 1. Update Story
      const { error: updateError } = await supabase
        .from('stories')
        .update({
          selected_title: selectedTitle?.title_text,
          selected_thumbnail_url: selectedThumb?.image_url,
          description: description,
          tags: tags.split(',').map(t => t.trim()), // Assume tags column accepts array, or adapt if string
          status: 'publishing'
        })
        .eq('id', id);

      if (updateError) throw updateError;

      // 2. Create Job
      const { error: jobError } = await supabase
        .from('jobs')
        .insert({
          story_id: id,
          job_type: 'upload_youtube',
          status: 'queued'
        });

      if (jobError) throw jobError;

      // 3. Redirect
      router.push(`/stories/${id}`);

    } catch (err) {
      console.error('Publish failed:', err);
      alert('Failed to start publishing process.');
    } finally {
      setPublishing(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center">Loading review data...</div>;
  }

  if (!story) {
    return <div className="p-8 text-center text-red-500">Story not found.</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Final Review</h1>
          <p className="text-muted-foreground">Select the best assets before publishing to YouTube.</p>
        </div>
        <Badge variant="outline" className="text-lg uppercase">
          {story.status}
        </Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left Column: Video & Metadata */}
        <div className="space-y-6">
          <Card className="overflow-hidden border-zinc-800 bg-zinc-950/50">
            <CardHeader>
              <CardTitle>Video Preview</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {videoUrl ? (
                <video 
                  controls 
                  className="w-full bg-black aspect-video" 
                  src={videoUrl}
                >
                  Your browser does not support the video tag.
                </video>
              ) : (
                <div className="flex h-64 items-center justify-center bg-zinc-900 text-zinc-500">
                  Video not available
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-950/30">
            <CardHeader>
              <CardTitle>Metadata</CardTitle>
              <CardDescription>Optimize for SEO</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="min-h-[150px] bg-zinc-900/50 font-mono text-sm"
                  placeholder="Video description..."
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tags">Tags (comma separated)</Label>
                <Input
                  id="tags"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  className="bg-zinc-900/50"
                  placeholder="history, mystery, archives..."
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Titles & Thumbs */}
        <div className="space-y-6">
          {/* Titles */}
          <Card className="border-zinc-800 bg-zinc-950/30">
            <CardHeader>
              <CardTitle>Select Title</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              {titles.length > 0 ? (
                titles.map((t) => (
                  <label
                    key={t.id}
                    className={`flex cursor-pointer items-center justify-between rounded-lg border p-4 transition-all hover:bg-zinc-900 ${
                      selectedTitleId === t.id
                        ? 'border-green-500 bg-green-950/10 ring-1 ring-green-500'
                        : 'border-zinc-800 bg-zinc-900/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="title"
                        value={t.id}
                        checked={selectedTitleId === t.id}
                        onChange={() => setSelectedTitleId(t.id)}
                        className="h-4 w-4 border-zinc-600 bg-zinc-900 text-green-500 focus:ring-green-500"
                      />
                      <span className="font-medium">{t.title_text}</span>
                    </div>
                  </label>
                ))
              ) : (
                <p className="text-sm text-zinc-500">No titles generated yet.</p>
              )}
            </CardContent>
          </Card>

          {/* Thumbnails */}
          <Card className="border-zinc-800 bg-zinc-950/30">
            <CardHeader>
              <CardTitle>Select Thumbnail</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {thumbnails.length > 0 ? (
                  thumbnails.map((thumb) => (
                    <div 
                      key={thumb.id} 
                      className="space-y-2"
                    >
                      <div
                        onClick={() => setSelectedThumbId(thumb.id)}
                        className={`relative cursor-pointer overflow-hidden rounded-lg border-2 transition-all ${
                          selectedThumbId === thumb.id
                            ? 'border-green-500 shadow-[0_0_15px_rgba(34,197,94,0.3)]'
                            : 'border-transparent hover:border-zinc-700'
                        }`}
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img 
                          src={thumb.image_url} 
                          alt={`Thumbnail v${thumb.version}`}
                          className="aspect-video w-full object-cover"
                        />
                        <div className="absolute right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs font-bold text-white backdrop-blur-sm">
                          v{thumb.version}
                        </div>
                      </div>
                      
                      <Input 
                        placeholder="Feedback for regeneration..."
                        className="h-8 text-xs bg-zinc-900/50 border-zinc-800"
                        value={thumbFeedback[thumb.id] || ''}
                        onChange={(e) => setThumbFeedback(prev => ({...prev, [thumb.id]: e.target.value}))}
                      />
                    </div>
                  ))
                ) : (
                   <p className="col-span-2 text-sm text-zinc-500">No thumbnails generated yet.</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Action */}
          <div className="pt-4">
            <Button
              size="lg"
              className="w-full bg-green-600 hover:bg-green-700 text-white font-bold text-lg h-14"
              disabled={!selectedTitleId || !selectedThumbId || publishing}
              onClick={handlePublish}
            >
              {publishing ? 'Publishing...' : 'CONFIRM & PUBLISH'}
            </Button>
            <p className="mt-2 text-center text-xs text-zinc-500">
              This will queue the video for YouTube upload.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
