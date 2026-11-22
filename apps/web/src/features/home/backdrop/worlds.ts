import {
    extractWorldFaces,
    type RenderableWorld,
    stripWorldBuffers,
    type WorldFaces,
} from './voxel-world';
import { buildCedarSanctuary } from './worlds/cedar-sanctuary';

export { buildCedarSanctuary };

let cachedCedarEntry: { world: RenderableWorld; faces: WorldFaces } | null = null;

/**
 * Returns the cached renderable Cedar Sanctuary diorama and pre-sorted visible
 * faces, releasing heavy `solid`/`emissive` build buffers immediately after
 * face extraction.
 */
export function getCedarWorldAndFaces(): { world: RenderableWorld; faces: WorldFaces } {
    if (cachedCedarEntry) return cachedCedarEntry;
    const full = buildCedarSanctuary();
    const faces = extractWorldFaces(full);
    cachedCedarEntry = { world: stripWorldBuffers(full), faces };
    return cachedCedarEntry;
}
