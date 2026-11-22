import { afterEach, describe, expect, it } from 'vitest';
import { extractWorldFaces, isValidWorldId, WORLD_IDS, WORLD_METADATA } from './voxel-world';
import { readPreferredWorld, WORLD_STORAGE_KEY, writePreferredWorld } from './world-storage';
import {
    buildBioluminescentReef,
    buildCedarSanctuary,
    buildMagmaForge,
    buildSkyObservatory,
    getWorldAndFaces,
} from './worlds';

describe('worlds (multi-world voxel dioramas & storage preference)', () => {
    afterEach(() => {
        window.localStorage.clear();
    });

    it('builds all 5 curated worlds deterministically with unique silhouettes and cached faces', () => {
        const voxelCounts = new Set<number>();

        for (const id of WORLD_IDS) {
            const first = getWorldAndFaces(id);
            const second = getWorldAndFaces(id);
            expect(first).toBe(second);

            expect(first.world.worldId).toBe(id);
            expect(first.world.voxelCount).toBeGreaterThan(2000);
            expect(first.world.lamps.length).toBeGreaterThan(0);
            expect(first.world.petals.length).toBeGreaterThan(0);
            expect(first.world.fireflies.length).toBe(16);
            expect(first.world.koi.length).toBeGreaterThanOrEqual(2);
            expect(first.faces.island.length).toBeGreaterThan(500);
            expect(first.faces.cloudsFar.length).toBeGreaterThan(40);
            expect(first.faces.cloudsNear.length).toBeGreaterThan(40);

            voxelCounts.add(first.world.voxelCount);
        }

        // Every world has distinct 3D geometry
        expect(voxelCounts.size).toBe(WORLD_IDS.length);
    });

    it('verifies seed determinism and monotonic painter depth order for each new world generator', () => {
        const generators = [
            buildMagmaForge,
            buildBioluminescentReef,
            buildSkyObservatory,
            buildCedarSanctuary,
        ];

        for (const buildFn of generators) {
            const a = buildFn();
            const b = buildFn();
            expect(a.voxelCount).toBe(b.voxelCount);
            expect(a.lamps).toEqual(b.lamps);
            const faces = extractWorldFaces(a);
            for (const layer of [faces.cloudsFar, faces.cloudsNear, faces.island]) {
                for (let i = 1; i < layer.length; i++) {
                    expect(layer[i][0]).toBeGreaterThanOrEqual(layer[i - 1][0]);
                }
            }
        }
    });

    it('assigns distinct particle modes and valid glow hues across all 5 world presets', () => {
        const modes = new Set(WORLD_IDS.map((id) => WORLD_METADATA[id].particleMode));
        expect(modes.size).toBe(5);
        expect(isValidWorldId('magma-forge')).toBe(true);
        expect(isValidWorldId('unknown-world')).toBe(false);
    });

    it('persists and restores valid world preferences safely in localStorage', () => {
        expect(readPreferredWorld()).toBeNull();

        window.localStorage.setItem(WORLD_STORAGE_KEY, 'not-a-world');
        expect(readPreferredWorld()).toBeNull();

        expect(writePreferredWorld('bioluminescent-reef')).toBe(true);
        expect(readPreferredWorld()).toBe('bioluminescent-reef');
    });
});
