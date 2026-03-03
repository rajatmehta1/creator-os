"use client";

import { useState } from "react";

interface MediaKitEditorProps {
  initialData?: {
    bio?: string;
    niche?: string;
    contactEmail?: string;
    socialLinks?: Record<string, string>;
    rateOverrides?: Record<string, number>;
  };
  onSave?: (data: Record<string, unknown>) => void;
}

export default function MediaKitEditor({ initialData, onSave }: MediaKitEditorProps) {
  const [bio, setBio] = useState(initialData?.bio || "");
  const [niche, setNiche] = useState(initialData?.niche || "");
  const [contactEmail, setContactEmail] = useState(initialData?.contactEmail || "");

  const handleSave = () => {
    onSave?.({ bio, niche, contactEmail });
  };

  return (
    <div className="space-y-6 rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold">Edit Media Kit</h2>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium">Creator Bio</label>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            className="mt-1 w-full rounded-md border bg-background p-3 text-sm"
            rows={4}
            placeholder="Write a brief bio about yourself and your channel..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium">Niche / Category</label>
          <input
            type="text"
            value={niche}
            onChange={(e) => setNiche(e.target.value)}
            className="mt-1 w-full rounded-md border bg-background p-2 text-sm"
            placeholder="e.g., Technology, Education, Entertainment"
          />
        </div>

        <div>
          <label className="block text-sm font-medium">Contact Email</label>
          <input
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            className="mt-1 w-full rounded-md border bg-background p-2 text-sm"
            placeholder="business@example.com"
          />
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <button className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent">
          Cancel
        </button>
        <button
          onClick={handleSave}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Save Changes
        </button>
      </div>
    </div>
  );
}
