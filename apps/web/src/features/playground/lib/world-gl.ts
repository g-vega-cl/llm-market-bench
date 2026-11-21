// biome-ignore-all lint/correctness/useHookAtTopLevel: gl.useProgram is a WebGL call, not a React hook
// Dependency-free WebGL2 voxel renderer: palette helpers plus pure GL functions. No React.

export type WorldTone = 'bullish' | 'bearish' | 'neutral';

export type WorldPalette = {
    background: readonly [number, number, number];
    low: readonly [number, number, number];
    high: readonly [number, number, number];
};

export type WorldUniforms = {
    time: WebGLUniformLocation | null;
    aspect: WebGLUniformLocation | null;
    pointer: WebGLUniformLocation | null;
};

export type WorldState = {
    program: WebGLProgram;
    vao: WebGLVertexArrayObject;
    buffer: WebGLBuffer;
    uniforms: WorldUniforms;
};

export type WorldInitResult =
    | { ok: true; state: WorldState }
    | { ok: false; reason: 'shader' | 'program' };

export type WorldFrame = {
    time: number;
    pointerX: number;
};

const COLUMNS = 40;
const ROWS = 30;
const SPACING_X = 1.55;
const SPACING_Z = 1.2;
const FLOATS_PER_INSTANCE = 5;
const BYTES_PER_FLOAT = 4;
const INSTANCE_STRIDE = FLOATS_PER_INSTANCE * BYTES_PER_FLOAT;

export const WORLD_INSTANCE_COUNT = COLUMNS * ROWS;

const VERTEX_SHADER = `#version 300 es
layout(location = 0) in float a_x;
layout(location = 1) in float a_z;
layout(location = 2) in float a_height;
layout(location = 3) in float a_phase;

uniform float u_time;
uniform float u_aspect;
uniform float u_pointer;
uniform vec3 u_low;
uniform vec3 u_high;

flat out vec3 v_color;
out float v_shade;

const vec2 CORNERS[6] = vec2[6](
    vec2(0.0, 0.0), vec2(1.0, 0.0), vec2(0.0, 1.0),
    vec2(0.0, 1.0), vec2(1.0, 0.0), vec2(1.0, 1.0)
);

const float HALF_HEIGHT = 22.0;
const float BOX_WIDTH = 1.2;

void main() {
    vec2 corner = CORNERS[gl_VertexID];
    float sway = sin(u_time + a_phase) * 0.05;
    // Isometric field: depth contributes to both axes, so 30 rows read as a
    // receding plain instead of stacking into one flat bar chart.
    float skew = 0.45 + u_pointer * 0.05;
    vec3 pos = vec3(a_x + (corner.x - 0.5) * BOX_WIDTH, corner.y * a_height + sway, a_z);
    float isoX = pos.x + pos.z * skew;
    float isoY = pos.y + pos.z * 0.22;

    gl_Position = vec4(
        isoX / (u_aspect * HALF_HEIGHT),
        (isoY - 4.0) / HALF_HEIGHT,
        (pos.z + 24.0) / 48.0,
        1.0
    );
    v_color = mix(u_low, u_high, clamp(a_height / 4.4, 0.0, 1.0));
    v_shade = corner.y;
}
`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;

flat in vec3 v_color;
in float v_shade;

out vec4 fragColor;

void main() {
    vec3 tinted = v_color * mix(0.58, 1.06, clamp(v_shade, 0.0, 1.0));
    fragColor = vec4(min(tinted, vec3(1.0)), 1.0);
}
`;

const TONE_VARS: Record<WorldTone, { low: string; high: string }> = {
    bullish: { low: '--color-accent', high: '--color-success' },
    bearish: { low: '--color-danger-dark', high: '--color-danger' },
    neutral: { low: '--color-voxel-bevel-hi', high: '--color-voxel-muted' },
};

const TONE_FALLBACKS: Record<WorldTone, { low: string; high: string }> = {
    bullish: { low: '#f0a830', high: '#68d391' },
    bearish: { low: '#381510', high: '#e56b55' },
    neutral: { low: '#3f574a', high: '#9eb0a3' },
};

const BACKGROUND_FALLBACK = '#141c18';

function createCssReader(): (name: string, fallback: string) => string {
    if (typeof document === 'undefined' || !document.documentElement) {
        return (_name, fallback) => fallback;
    }
    try {
        const styles = getComputedStyle(document.documentElement);
        return (name, fallback) => {
            const value = styles.getPropertyValue(name).trim();
            return value.length > 0 ? value : fallback;
        };
    } catch {
        return (_name, fallback) => fallback;
    }
}

function hexToRgb(value: string): [number, number, number] | null {
    const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(value.trim());
    if (!match) return null;
    const raw = match[1];
    const hex = raw.length === 3 ? raw.replace(/./g, (char) => char + char) : raw;
    const int = Number.parseInt(hex, 16);
    return [((int >> 16) & 255) / 255, ((int >> 8) & 255) / 255, (int & 255) / 255];
}

function parseColor(value: string, fallback: string): [number, number, number] {
    return hexToRgb(value) ?? hexToRgb(fallback) ?? [0, 0, 0];
}

/** Reads the three-tone palette from the page theme, with hex constants as fallback. */
export function resolveWorldPalette(tone: WorldTone): WorldPalette {
    const read = createCssReader();
    const vars = TONE_VARS[tone];
    const fallback = TONE_FALLBACKS[tone];
    return {
        background: parseColor(
            read('--color-voxel-canvas', BACKGROUND_FALLBACK),
            BACKGROUND_FALLBACK,
        ),
        low: parseColor(read(vars.low, fallback.low), fallback.low),
        high: parseColor(read(vars.high, fallback.high), fallback.high),
    };
}

function hash01(seed: number): number {
    let x = (seed | 0) + 0x9e3779b9;
    x = Math.imul(x ^ (x >>> 16), 0x45d9f3b);
    x = Math.imul(x ^ (x >>> 16), 0x45d9f3b);
    x ^= x >>> 16;
    return (x >>> 0) / 0xffffffff;
}

/** Deterministic height field; identical on every load so renders are reproducible. */
function buildInstanceData(): Float32Array {
    const data = new Float32Array(WORLD_INSTANCE_COUNT * FLOATS_PER_INSTANCE);
    const halfW = (COLUMNS - 1) / 2;
    const halfD = (ROWS - 1) / 2;
    let cursor = 0;
    for (let row = 0; row < ROWS; row += 1) {
        for (let col = 0; col < COLUMNS; col += 1) {
            const seed = row * COLUMNS + col;
            const wave = Math.sin(col * 0.34 + row * 0.19) * 1.1;
            const noise = (hash01(seed * 2 + 1) - 0.5) * 2.2;
            const height = Math.min(4.2, Math.max(0.5, 2.2 + wave + noise));
            data[cursor] = (col - halfW) * SPACING_X; // a_x
            data[cursor + 1] = (row - halfD) * SPACING_Z; // a_z
            data[cursor + 2] = height; // a_height
            data[cursor + 3] = hash01(seed * 2 + 2) * Math.PI * 2; // a_phase
            cursor += FLOATS_PER_INSTANCE;
        }
    }
    return data;
}

function compileShader(
    gl: WebGL2RenderingContext,
    type: number,
    source: string,
): WebGLShader | null {
    const shader = gl.createShader(type);
    if (!shader) return null;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        gl.deleteShader(shader);
        return null;
    }
    return shader;
}

function bindInstanceAttribute(gl: WebGL2RenderingContext, location: number, offset: number): void {
    gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location, 1, gl.FLOAT, false, INSTANCE_STRIDE, offset);
    gl.vertexAttribDivisor(location, 1);
}

export function initWorld(gl: WebGL2RenderingContext, palette: WorldPalette): WorldInitResult {
    const vertex = compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
    const fragment = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
    if (!vertex || !fragment) {
        if (vertex) gl.deleteShader(vertex);
        if (fragment) gl.deleteShader(fragment);
        return { ok: false, reason: 'shader' };
    }

    const program = gl.createProgram();
    if (!program) {
        gl.deleteShader(vertex);
        gl.deleteShader(fragment);
        return { ok: false, reason: 'program' };
    }
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        gl.deleteProgram(program);
        gl.deleteShader(vertex);
        gl.deleteShader(fragment);
        return { ok: false, reason: 'program' };
    }
    // Linked: the shader objects are no longer needed and the program keeps them alive.
    gl.deleteShader(vertex);
    gl.deleteShader(fragment);

    const vao = gl.createVertexArray();
    const buffer = gl.createBuffer();
    if (!vao || !buffer) {
        if (vao) gl.deleteVertexArray(vao);
        if (buffer) gl.deleteBuffer(buffer);
        gl.deleteProgram(program);
        return { ok: false, reason: 'program' };
    }

    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, buildInstanceData(), gl.STATIC_DRAW);
    bindInstanceAttribute(gl, 0, 0);
    bindInstanceAttribute(gl, 1, BYTES_PER_FLOAT);
    bindInstanceAttribute(gl, 2, BYTES_PER_FLOAT * 2);
    bindInstanceAttribute(gl, 3, BYTES_PER_FLOAT * 3);
    gl.bindVertexArray(null);

    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.useProgram(program);
    gl.clearColor(palette.background[0], palette.background[1], palette.background[2], 1);
    gl.uniform3f(
        gl.getUniformLocation(program, 'u_low'),
        palette.low[0],
        palette.low[1],
        palette.low[2],
    );
    gl.uniform3f(
        gl.getUniformLocation(program, 'u_high'),
        palette.high[0],
        palette.high[1],
        palette.high[2],
    );

    const state: WorldState = {
        program,
        vao,
        buffer,
        uniforms: {
            time: gl.getUniformLocation(program, 'u_time'),
            aspect: gl.getUniformLocation(program, 'u_aspect'),
            pointer: gl.getUniformLocation(program, 'u_pointer'),
        },
    };
    return { ok: true, state };
}

export function drawWorld(gl: WebGL2RenderingContext, state: WorldState, frame: WorldFrame): void {
    const aspect = (gl.drawingBufferWidth || 1) / (gl.drawingBufferHeight || 1);
    const pointerX = Math.max(-1, Math.min(1, frame.pointerX));
    gl.useProgram(state.program);
    gl.bindVertexArray(state.vao);
    gl.uniform1f(state.uniforms.time, frame.time);
    gl.uniform1f(state.uniforms.aspect, aspect);
    gl.uniform1f(state.uniforms.pointer, pointerX);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, WORLD_INSTANCE_COUNT);
}

export function disposeWorld(gl: WebGL2RenderingContext, state: WorldState): void {
    gl.deleteBuffer(state.buffer);
    gl.deleteVertexArray(state.vao);
    gl.deleteProgram(state.program);
}
