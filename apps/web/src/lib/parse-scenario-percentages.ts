export interface ParsedScenario {
    rawHeader: string;
    cleanHeader: string;
    percentage: string | null;
    outcome: string;
    tradingPlan: string | null;
    fullText: string;
}

function parsePreamble(preamble: string): ParsedScenario[] {
    const lines = preamble
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);
    return lines.map((line) => ({
        rawHeader: '',
        cleanHeader: '',
        percentage: extractPercentage(line),
        outcome: line,
        tradingPlan: null,
        fullText: line,
    }));
}

function parseScenarioBlock(header: string, body: string): ParsedScenario {
    const pct = extractPercentage(body) || extractPercentage(header);
    const cleanHeader = header.replace(/\s*\([^)]*%\s*probability\)/i, '').trim();

    const [outcomePart, tradingPlanPart] = body.split(/Trading Plan.*?:/);
    const outcome = outcomePart ? outcomePart.replace(/\s*->\s*$/, '').trim() : '';
    const tradingPlan = tradingPlanPart ? tradingPlanPart.trim() : null;

    return {
        rawHeader: header,
        cleanHeader,
        percentage: pct,
        outcome,
        tradingPlan,
        fullText: `${header}${body}`.replace(/\s+/g, ' ').trim(),
    };
}

export function parseScenarios(analysis: string): ParsedScenario[] {
    if (!analysis) {
        return [];
    }

    const cleanAnalysis = analysis.split('**Investable Assets')[0].trim();
    const scenarioRegex = /(Scenario [A-Z][^:]*:)/;

    if (scenarioRegex.test(cleanAnalysis)) {
        const parts = cleanAnalysis.split(scenarioRegex);
        const results: ParsedScenario[] = [];

        // Preamble before the first scenario
        if (parts[0]?.trim()) {
            results.push(...parsePreamble(parts[0]));
        }

        // Process each scenario block
        for (let i = 1; i < parts.length; i += 2) {
            results.push(parseScenarioBlock(parts[i], parts[i + 1] || ''));
        }

        return results;
    }

    // Fallback: original split by newline
    return parsePreamble(cleanAnalysis);
}

export function parseScenarioPercentages(
    analysis: string,
): { text: string; percentage: string | null }[] {
    if (!analysis) {
        return [{ text: '', percentage: null }];
    }
    const scenarios = parseScenarios(analysis);
    return scenarios.map((s) => ({
        text: s.fullText,
        percentage: s.percentage,
    }));
}

export function extractPercentage(text: string): string | null {
    const match = text.match(/(\d{1,3})\s*%/);
    return match ? `${match[1]}%` : null;
}
