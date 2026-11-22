import type { ParticleMode } from './voxel-world';

export interface ParticlePresetConfig {
    driftColors: [string, string];
    floaterColors: [string, string];
    glintHex: string;
    rippleHex: string;
    rippleSpeed: number;
    haloAlwaysOn: boolean;
}

/**
 * Single authoritative registry for particle colors, ripple kinematics, and halo behavior
 * shared between GardenBackdrop layer baking and the canvas particle renderer.
 */
export const PARTICLE_PRESETS: Record<ParticleMode, ParticlePresetConfig> = {
    sakura: {
        driftColors: ['#f7cad8', '#f8e6dc'],
        floaterColors: ['#9ef0c0', '#ffe38e'],
        glintHex: '#e2eee8',
        rippleHex: '#daf0e8',
        rippleSpeed: 0.45,
        haloAlwaysOn: false,
    },
    embers: {
        driftColors: ['#ff7b36', '#ffd275'],
        floaterColors: ['#ff9c42', '#ffdf70'],
        glintHex: '#ffc65c',
        rippleHex: '#ff863e',
        rippleSpeed: 0.78,
        haloAlwaysOn: true,
    },
    spores: {
        driftColors: ['#7df7d8', '#c0b2ff'],
        floaterColors: ['#6cf5d4', '#b3a3ff'],
        glintHex: '#7ef8e0',
        rippleHex: '#7ef4da',
        rippleSpeed: 0.36,
        haloAlwaysOn: true,
    },
    'star-runes': {
        driftColors: ['#fff0b8', '#a6ecff'],
        floaterColors: ['#a8f0ff', '#ffe28f'],
        glintHex: '#c6ecff',
        rippleHex: '#f5dc98',
        rippleSpeed: 0.52,
        haloAlwaysOn: true,
    },
    'cedar-mist': {
        driftColors: ['#e89648', '#f2c86b'],
        floaterColors: ['#c6f2bd', '#ffd880'],
        glintHex: '#d6ecea',
        rippleHex: '#cceae4',
        rippleSpeed: 0.58,
        haloAlwaysOn: false,
    },
};
