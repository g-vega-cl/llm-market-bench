import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';

interface WaitlistPledgeModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (email: string, tier: string, feedback: string) => Promise<void>;
}

export function WaitlistPledgeModal({ isOpen, onClose, onSubmit }: WaitlistPledgeModalProps) {
    const [email, setEmail] = useState('');
    const [tier, setTier] = useState('supporter');
    const [feedback, setFeedback] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isSubmitted, setIsSubmitted] = useState(false);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email) return;

        setIsSubmitting(true);
        try {
            await onSubmit(email, tier, feedback);
            setIsSubmitted(true);
        } catch {
            // Handled by parent or toast
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="flex w-full max-w-lg flex-col gap-4 border border-voxel-bevel-hi bg-voxel-surface p-6 rounded-none voxel-card">
                <div className="flex items-center justify-between border-b border-voxel-bevel-hi pb-3">
                    <div className="flex items-center gap-2">
                        <span className="font-display text-sm font-bold text-voxel-ink">
                            Early Supporter Pledge
                        </span>
                        <Badge variant="soft" size="sm">
                            Free Beta
                        </Badge>
                    </div>
                    <Button
                        type="button"
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        onClick={onClose}
                    >
                        ✕
                    </Button>
                </div>

                {isSubmitted ? (
                    <div className="flex flex-col items-center gap-3 py-6 text-center">
                        <span className="font-display text-sm font-bold text-success">
                            Pledge Received!
                        </span>
                        <p className="text-xs font-normal text-voxel-muted">
                            Thank you for backing independent AI strategy research. We have recorded
                            your interest and will notify you when dedicated GPU clusters open.
                        </p>
                        <Button size="sm" onClick={onClose}>
                            Return to Studio
                        </Button>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                        <div className="voxel-trough p-3 text-xs font-normal text-voxel-muted">
                            <b className="text-voxel-ink">100% Free Tier:</b> Strategy recipes and
                            backtests currently run at no cost on our local GPU queue
                            (`auto-strata`). Paid compute tiers and dedicated high-frequency slots
                            are on our roadmap.
                        </div>

                        <label className="flex flex-col gap-1 text-xs font-normal text-voxel-muted">
                            <span>Your Email Address</span>
                            <input
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="name@domain.com"
                                className="border border-voxel-bevel-hi bg-voxel-canvas p-2 text-sm font-bold text-voxel-ink rounded-none focus:outline-none"
                            />
                        </label>

                        <label className="flex flex-col gap-1 text-xs font-normal text-voxel-muted">
                            <span>Intended Supporter Tier</span>
                            <select
                                value={tier}
                                onChange={(e) => setTier(e.target.value)}
                                className="border border-voxel-bevel-hi bg-voxel-canvas p-2 text-sm font-bold text-voxel-ink rounded-none"
                            >
                                <option value="supporter">
                                    Pro Researcher ($19/mo - Priority GPU queue & 5-minute ticks)
                                </option>
                                <option value="live_trader">
                                    Live Quant ($49/mo - Sub-minute live alert triggers & webhook
                                    API)
                                </option>
                                <option value="custom">Institutional / Enterprise Partner</option>
                            </select>
                        </label>

                        <label className="flex flex-col gap-1 text-xs font-normal text-voxel-muted">
                            <span>What strategies or data would you like to see?</span>
                            <textarea
                                rows={3}
                                value={feedback}
                                onChange={(e) => setFeedback(e.target.value)}
                                placeholder="e.g. Options flow block, Level 2 book pressure, Polymarket prediction markets..."
                                className="border border-voxel-bevel-hi bg-voxel-canvas p-2 text-xs font-normal text-voxel-ink rounded-none"
                            />
                        </label>

                        <div className="flex justify-end gap-2 border-t border-voxel-bevel-hi pt-3">
                            <Button variant="outline" size="sm" type="button" onClick={onClose}>
                                Cancel
                            </Button>
                            <Button size="sm" type="submit" disabled={isSubmitting || !email}>
                                {isSubmitting ? 'Saving...' : 'Pledge Support'}
                            </Button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
