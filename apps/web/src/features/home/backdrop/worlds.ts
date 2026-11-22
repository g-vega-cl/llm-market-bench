import { buildGarden } from './garden-world';
import {
    extractWorldFaces,
    type RenderableWorld,
    stripWorldBuffers,
    type VoxelWorld,
    type WorldFaces,
    type WorldId,
} from './voxel-world';
import { buildBioluminescentReef } from './worlds/bioluminescent-reef';
import { buildCedarSanctuary } from './worlds/cedar-sanctuary';
import { buildMagmaForge } from './worlds/magma-forge';
import { buildSkyObservatory } from './worlds/sky-observatory';

export { buildBioluminescentReef, buildCedarSanctuary, buildMagmaForge, buildSkyObservatory };

const worldCache = new Map<WorldId, { world: RenderableWorld; faces: WorldFaces }>();

const WORLD_BUILDERS: Record<WorldId, () => VoxelWorld> = {
    'sakura-garden': () => buildGarden(),
    'magma-forge': () => buildMagmaForge(),
    'bioluminescent-reef': () => buildBioluminescentReef(),
    'sky-observatory': () => buildSkyObservatory(),
    'cedar-sanctuary': () => buildCedarSanctuary(),
};

/**
 * Returns the cached renderable world and pre-sorted visible faces for any
 * curated diorama id, releasing heavy `solid`/`emissive` build buffers once
 * faces are extracted.
 */
export function getWorldAndFaces(worldId: WorldId): { world: RenderableWorld; faces: WorldFaces } {
    const existing = worldCache.get(worldId);
    if (existing) return existing;
    const full = WORLD_BUILDERS[worldId]();
    const faces = extractWorldFaces(full);
    const entry = { world: stripWorldBuffers(full), faces };
    worldCache.set(worldId, entry);
    return entry;
}
