import { PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type { LegalDocument } from './legal-content';

export interface LegalPageProps {
    document: LegalDocument;
}

export function LegalPage({ document }: LegalPageProps) {
    return (
        <div className="min-h-screen text-voxel-ink">
            <PageLayout maxWidth="sm" className="flex flex-col gap-10">
                <header className="flex flex-col gap-3">
                    <p className="text-sm font-normal uppercase tracking-[0.28em] text-accent">
                        Benchify
                    </p>
                    <h1 className="text-lg font-bold text-display text-voxel-ink">
                        {document.title}
                    </h1>
                    <p className="text-sm font-normal text-voxel-muted">
                        Updated {document.updated}
                    </p>
                    <p className="text-sm leading-relaxed text-voxel-muted">{document.intro}</p>
                </header>

                <div className="flex flex-col gap-8">
                    {document.sections.map((section) => (
                        <section key={section.heading} className="flex flex-col gap-3">
                            <SectionHeading>{section.heading}</SectionHeading>
                            {section.paragraphs?.map((paragraph) => (
                                <p
                                    key={paragraph}
                                    className="text-sm leading-relaxed text-voxel-muted"
                                >
                                    {paragraph}
                                </p>
                            ))}
                            {section.bullets ? (
                                <ul className="list-disc pl-5 flex flex-col gap-2 text-sm leading-relaxed text-voxel-muted">
                                    {section.bullets.map((bullet) => (
                                        <li key={bullet}>{bullet}</li>
                                    ))}
                                </ul>
                            ) : null}
                        </section>
                    ))}
                </div>

                <footer className="border-t-2 border-voxel-bevel-lo pt-6 flex flex-wrap gap-4 text-sm font-normal">
                    <Link to="/privacy" className="text-accent hover:underline">
                        Privacy
                    </Link>
                    <Link to="/terms" className="text-accent hover:underline">
                        Terms
                    </Link>
                    <Link to="/disclaimer" className="text-accent hover:underline">
                        Disclaimer
                    </Link>
                    <Link to="/" className="text-voxel-muted hover:text-voxel-ink">
                        Back home
                    </Link>
                </footer>
            </PageLayout>
        </div>
    );
}
