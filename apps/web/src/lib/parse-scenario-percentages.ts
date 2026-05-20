export function parseScenarioPercentages(
    analysis: string,
): { text: string; percentage: string | null }[] {
    if (!analysis) {
        return [{ text: '', percentage: null }];
    }

    const cleanAnalysis = analysis.split('**Investable Assets')[0].trim();
    const scenarioRegex = /(Scenario [A-Z][^:]*:)/;

    if (scenarioRegex.test(cleanAnalysis)) {
        const parts = cleanAnalysis.split(scenarioRegex);
        const results: { text: string; percentage: string | null }[] = [];

        // Preamble before the first scenario
        if (parts[0]?.trim()) {
            const lines = parts[0]
                .split('\n')
                .map((line) => line.trim())
                .filter(Boolean);
            for (const line of lines) {
                results.push({
                    text: line,
                    percentage: extractPercentage(line),
                });
            }
        }

        // Process each scenario block
        for (let i = 1; i < parts.length; i += 2) {
            const header = parts[i];
            const body = parts[i + 1] || '';

            const fullText = `${header}${body}`.replace(/\s+/g, ' ').trim();
            const percentage = extractPercentage(body) || extractPercentage(header);

            results.push({
                text: fullText,
                percentage,
            });
        }

        return results;
    }

    // Fallback: original split by newline
    const lines = cleanAnalysis.split('\n');
    return lines.map((line) => {
        const percentage = extractPercentage(line);
        return { text: line, percentage };
    });
}

export function extractPercentage(text: string): string | null {
    const match = text.match(/(\d{1,3})\s*%/);
    return match ? `${match[1]}%` : null;
}
