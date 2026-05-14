export function parseScenarioPercentages(
    analysis: string,
): { text: string; percentage: string | null }[] {
    const lines = analysis.split('\n');
    return lines.map((line) => {
        const percentage = extractPercentage(line);
        return { text: line, percentage };
    });
}

export function extractPercentage(text: string): string | null {
    const match = text.match(/(\d{1,3})\s*%/);
    return match ? `${match[1]}%` : null;
}
