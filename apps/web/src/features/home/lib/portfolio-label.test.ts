import { describe, expect, it } from 'vitest';
import { portfolioLabel } from './portfolio-label';

describe('portfolioLabel', () => {
    it('drops the sys- prefix and title-cases the words', () => {
        expect(portfolioLabel('sys-max-pain')).toBe('Max Pain');
        expect(portfolioLabel('sys-sector-uncorr-7d')).toBe('Sector Uncorr 7d');
    });

    it('keeps short model tokens uppercase', () => {
        expect(portfolioLabel('sys-daily-spy-demo-model')).toBe('Daily SPY Demo Model');
    });

    it('splits on underscores and slashes', () => {
        expect(portfolioLabel('sys-daily-tlt-close-~typesafe/jev-latest')).toBe(
            'Daily TLT Close Jev',
        );
    });

    it('leaves llm owner ids readable', () => {
        expect(portfolioLabel('gemini-3.5-flash-lite')).toBe('Gemini 3.5 Flash Lite');
    });
});
