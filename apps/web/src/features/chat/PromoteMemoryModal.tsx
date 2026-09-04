import { Badge, Button, Card } from '@llm-market-bench/ui-design-system';
import type React from 'react';
import { useEffect, useState } from 'react';
import type { ChatMemory, DistillMemoryResult, SaveChatMemoryRequest } from './chat-types';

export interface PromoteMemoryModalProps {
    isOpen: boolean;
    onClose: () => void;
    userQuery: string;
    assistantResponse: string;
    initialData: DistillMemoryResult;
    onSave: (payload: SaveChatMemoryRequest) => Promise<ChatMemory>;
    onRedistill: (instruction: string) => Promise<DistillMemoryResult>;
    onSavedSuccess: (memory: ChatMemory) => void;
}

export function PromoteMemoryModal({
    isOpen,
    onClose,
    userQuery,
    assistantResponse: _assistantResponse,
    initialData,
    onSave,
    onRedistill,
    onSavedSuccess,
}: PromoteMemoryModalProps) {
    const [ticker, setTicker] = useState(initialData.ticker || '');
    const [thesis, setThesis] = useState(initialData.thesis || '');
    const [importanceScore, setImportanceScore] = useState<number>(
        initialData.importance_score || 7,
    );
    const [tags, setTags] = useState<string[]>(initialData.tags || []);
    const [tagInput, setTagInput] = useState('');
    const [customInstruction, setCustomInstruction] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [isRedistilling, setIsRedistilling] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Sync state when initialData changes
    useEffect(() => {
        setTicker(initialData.ticker || '');
        setThesis(initialData.thesis || '');
        setImportanceScore(initialData.importance_score || 7);
        setTags(initialData.tags || []);
        setError(null);
    }, [initialData]);

    if (!isOpen) return null;

    const handleAddTag = (e: React.KeyboardEvent | React.MouseEvent) => {
        if ('key' in e && e.key !== 'Enter') return;
        e.preventDefault();
        const trimmed = tagInput.trim().toLowerCase();
        if (trimmed && !tags.includes(trimmed)) {
            setTags([...tags, trimmed]);
            setTagInput('');
        }
    };

    const handleRemoveTag = (tagToRemove: string) => {
        setTags(tags.filter((t) => t !== tagToRemove));
    };

    const applyDistilledUpdate = (updated: DistillMemoryResult) => {
        if (updated.ticker) setTicker(updated.ticker);
        if (updated.thesis) setThesis(updated.thesis);
        if (updated.importance_score) setImportanceScore(updated.importance_score);
        if (updated.tags && updated.tags.length > 0) setTags(updated.tags);
    };

    const handleRedistill = async () => {
        if (!customInstruction.trim() || isRedistilling) return;
        setIsRedistilling(true);
        setError(null);
        try {
            const updated = await onRedistill(customInstruction.trim());
            applyDistilledUpdate(updated);
            setCustomInstruction('');
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Failed to re-distill memory';
            setError(msg);
        } finally {
            setIsRedistilling(false);
        }
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!thesis.trim() || isSaving) return;

        setIsSaving(true);
        setError(null);
        try {
            const saved = await onSave({
                ticker: ticker.trim() ? ticker.trim().toUpperCase() : undefined,
                thesis: thesis.trim(),
                tags,
                importance_score: Math.min(10, Math.max(1, importanceScore)),
                sourceQuery: userQuery,
            });
            onSavedSuccess(saved);
            onClose();
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Failed to save memory';
            setError(msg);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
            <Card className="w-full max-w-lg border-cyan-900/50 bg-zinc-950/95 p-6 shadow-2xl space-y-5 text-zinc-200">
                {/* Header */}
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                    <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-base">
                            🧠
                        </div>
                        <div>
                            <h3 className="font-semibold text-white text-sm">
                                Promote Insight to Private Memory
                            </h3>
                            <p className="text-[11px] text-zinc-400">
                                Strictly isolated in your personal research vault
                            </p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-lg p-1 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
                    >
                        ✕
                    </button>
                </div>

                {error && (
                    <div className="rounded-xl border border-red-500/30 bg-red-950/30 p-2.5 text-xs text-red-300">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSave} className="space-y-4">
                    {/* Ticker & Score Row */}
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                            <label
                                htmlFor="promote-ticker"
                                className="text-[11px] font-medium text-zinc-400"
                            >
                                Stock Ticker (Optional)
                            </label>
                            <input
                                id="promote-ticker"
                                type="text"
                                value={ticker}
                                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                                placeholder="e.g. NVO, NVDA"
                                className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 px-3 py-2 text-xs text-zinc-100 font-mono placeholder:text-zinc-600 focus:border-cyan-500 focus:outline-none"
                            />
                        </div>

                        <div className="space-y-1">
                            <label
                                htmlFor="promote-score"
                                className="text-[11px] font-medium text-zinc-400"
                            >
                                Importance Score (1-10)
                            </label>
                            <input
                                id="promote-score"
                                type="number"
                                min={1}
                                max={10}
                                value={importanceScore}
                                onChange={(e) => setImportanceScore(Number(e.target.value))}
                                className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 px-3 py-2 text-xs text-zinc-100 font-mono focus:border-cyan-500 focus:outline-none"
                            />
                        </div>
                    </div>

                    {/* Thesis */}
                    <div className="space-y-1">
                        <label
                            htmlFor="promote-thesis"
                            className="text-[11px] font-medium text-zinc-400"
                        >
                            Distilled Market Thesis (Editable)
                        </label>
                        <textarea
                            id="promote-thesis"
                            rows={4}
                            value={thesis}
                            onChange={(e) => setThesis(e.target.value)}
                            required
                            placeholder="State the core catalyst, mechanism, and actionable conclusion..."
                            className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 p-3 text-xs leading-relaxed text-zinc-100 placeholder:text-zinc-600 focus:border-cyan-500 focus:outline-none resize-y"
                        />
                    </div>

                    {/* Tags */}
                    <div className="space-y-1.5">
                        <label
                            htmlFor="promote-tag-input"
                            className="text-[11px] font-medium text-zinc-400"
                        >
                            Topic Tags
                        </label>
                        <div className="flex flex-wrap gap-1.5 mb-1.5">
                            {tags.map((tag) => (
                                <Badge
                                    key={tag}
                                    variant="outline"
                                    size="sm"
                                    colorScheme="accent"
                                    className="gap-1 text-[10px]"
                                >
                                    <span>{tag}</span>
                                    <button
                                        type="button"
                                        onClick={() => handleRemoveTag(tag)}
                                        className="hover:text-red-400 ml-0.5"
                                    >
                                        ×
                                    </button>
                                </Badge>
                            ))}
                        </div>
                        <div className="flex gap-2">
                            <input
                                id="promote-tag-input"
                                type="text"
                                value={tagInput}
                                onChange={(e) => setTagInput(e.target.value)}
                                onKeyDown={handleAddTag}
                                placeholder="Add a tag..."
                                className="flex-1 rounded-xl border border-zinc-800 bg-zinc-900/80 px-3 py-1.5 text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-cyan-500 focus:outline-none"
                            />
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                colorScheme="neutral"
                                onClick={handleAddTag}
                            >
                                Add
                            </Button>
                        </div>
                    </div>

                    {/* Refinement instruction */}
                    <div className="pt-2 border-t border-zinc-800/80 space-y-1.5">
                        <label
                            htmlFor="promote-refine"
                            className="text-[11px] font-medium text-zinc-400"
                        >
                            Refinement Instruction (Optional)
                        </label>
                        <div className="flex gap-2">
                            <input
                                id="promote-refine"
                                type="text"
                                value={customInstruction}
                                onChange={(e) => setCustomInstruction(e.target.value)}
                                placeholder="e.g. Focus on supply bottleneck timing..."
                                className="flex-1 rounded-xl border border-zinc-800 bg-zinc-900/80 px-3 py-1.5 text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-cyan-500 focus:outline-none"
                            />
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                colorScheme="accent"
                                disabled={!customInstruction.trim() || isRedistilling}
                                onClick={handleRedistill}
                            >
                                {isRedistilling ? 'Distilling...' : 'Re-distill'}
                            </Button>
                        </div>
                    </div>

                    {/* Footer Actions */}
                    <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800">
                        <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            colorScheme="neutral"
                            onClick={onClose}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            variant="solid"
                            size="sm"
                            colorScheme="accent"
                            disabled={!thesis.trim() || isSaving}
                        >
                            {isSaving ? 'Saving...' : 'Save to My Theses'}
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
}
