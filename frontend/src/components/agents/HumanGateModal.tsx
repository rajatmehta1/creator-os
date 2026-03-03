"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface HumanGateModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentName: string;
  gateName: string;
  output: string;
  onApprove: (output: string) => void;
  onReject: (reason?: string) => void;
}

export default function HumanGateModal({
  isOpen,
  onClose,
  agentName,
  gateName,
  output,
  onApprove,
  onReject,
}: HumanGateModalProps) {
  const [mode, setMode] = useState<"review" | "edit">("review");
  const [editedOutput, setEditedOutput] = useState(output);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectInput, setShowRejectInput] = useState(false);

  // Reset state when modal opens with new output
  function resetState() {
    setMode("review");
    setEditedOutput(output);
    setRejectReason("");
    setShowRejectInput(false);
  }

  if (!isOpen) return null;

  function handleApprove() {
    onApprove(mode === "edit" ? editedOutput : output);
    resetState();
  }

  function handleReject() {
    if (showRejectInput) {
      onReject(rejectReason || undefined);
      resetState();
    } else {
      setShowRejectInput(true);
    }
  }

  function handleClose() {
    resetState();
    onClose();
  }

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="w-full max-w-2xl rounded-lg border bg-card shadow-xl"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b px-6 py-4">
            <div>
              <h2 className="text-lg font-semibold">Human Review Required</h2>
              <p className="text-sm text-muted-foreground">
                <span className="font-medium text-primary">{agentName}</span>
                {" "}- {gateName}
              </p>
            </div>
            <button
              onClick={handleClose}
              className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
                <path
                  d="M4 4L12 12M12 4L4 12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>

          {/* Mode Toggle */}
          <div className="flex gap-1 border-b px-6 py-2">
            <button
              onClick={() => setMode("review")}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                mode === "review"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent"
              )}
            >
              Review
            </button>
            <button
              onClick={() => {
                setMode("edit");
                setEditedOutput(output);
              }}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                mode === "edit"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent"
              )}
            >
              Edit
            </button>
          </div>

          {/* Content */}
          <div className="max-h-96 overflow-y-auto px-6 py-4">
            {mode === "review" ? (
              <div className="rounded-md border bg-secondary/30 p-4">
                <pre className="whitespace-pre-wrap text-sm leading-relaxed text-foreground font-sans">
                  {output}
                </pre>
              </div>
            ) : (
              <textarea
                value={editedOutput}
                onChange={(e) => setEditedOutput(e.target.value)}
                className="w-full min-h-[200px] rounded-md border bg-background p-4 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-y"
                placeholder="Edit the agent output..."
              />
            )}

            {/* Reject reason input */}
            {showRejectInput && (
              <div className="mt-4">
                <label className="text-xs font-medium text-muted-foreground">
                  Rejection reason (optional)
                </label>
                <input
                  type="text"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Why are you rejecting this output?"
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  autoFocus
                />
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 border-t px-6 py-4">
            <button
              onClick={handleReject}
              className={cn(
                "inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium transition-colors",
                showRejectInput
                  ? "border-destructive/20 bg-destructive/10 text-destructive hover:bg-destructive/20"
                  : "text-muted-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/20"
              )}
            >
              {showRejectInput ? "Confirm Reject" : "Reject"}
            </button>
            <button
              onClick={handleApprove}
              className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              {mode === "edit" ? "Approve with Edits" : "Approve"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
