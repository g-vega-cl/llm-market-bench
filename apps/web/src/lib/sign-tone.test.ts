import { describe, expect, it } from 'vitest';
import { signTone, signToneOrMuted } from './sign-tone';

describe('signTone', () => {
    it('maps a gain to the positive tone and a loss to the negative tone', () => {
        expect(signTone(12.5)).toBe('positive');
        expect(signTone(-0.01)).toBe('negative');
        expect(signTone('-3.4')).toBe('negative');
        expect(signTone('2.1')).toBe('positive');
    });

    it('treats a flat zero as muted, not as a gain', () => {
        expect(signTone(0)).toBe('muted');
        expect(signTone('0')).toBe('muted');
    });

    it('leaves unknown values neutral', () => {
        expect(signTone(null)).toBeUndefined();
        expect(signTone(undefined)).toBeUndefined();
        expect(signTone('N/A')).toBeUndefined();
        expect(signTone('')).toBeUndefined();
        expect(signTone('   ')).toBeUndefined();
        expect(signTone(Number.NaN)).toBeUndefined();
        expect(signTone(Number.POSITIVE_INFINITY)).toBeUndefined();
    });
});

describe('signToneOrMuted', () => {
    it('falls back to muted for values it cannot read', () => {
        expect(signToneOrMuted(null)).toBe('muted');
        expect(signToneOrMuted('N/A')).toBe('muted');
        expect(signToneOrMuted('')).toBe('muted');
    });

    it('keeps the signed tones', () => {
        expect(signToneOrMuted(4.2)).toBe('positive');
        expect(signToneOrMuted(-4.2)).toBe('negative');
        expect(signToneOrMuted(0)).toBe('muted');
    });
});
