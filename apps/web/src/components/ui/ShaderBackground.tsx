import { useEffect, useRef } from 'react';

const SHADERS = {
    pointillism: `
    precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec3 u_baseColor;
    uniform vec3 u_accentColor;
    varying vec2 v_texCoord;

    float random(vec2 st) {
        return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
    }

    void main() {
        vec2 uv = v_texCoord;
        // Fix aspect ratio so dots aren't stretched horizontally
        uv.x *= u_resolution.x / u_resolution.y;
        
        // Increased from 40.0 to 150.0 to make dots much smaller and higher resolution
        float size = 150.0;
        if(mod(floor(uv.y * size), 2.0) == 0.0) uv.x += 0.5 / size;
        
        vec2 g = floor(uv * size);
        vec2 f = fract(uv * size) - 0.5;
        
        float n = random(g);
        float glow = 0.5 + 0.4 * cos(u_time * 0.5 + n * 10.0);
        float d = length(f);
        
        float circle = smoothstep(0.3, 0.1, d); // Softer, smaller circle
        
        vec3 col = mix(u_baseColor, u_accentColor, circle * glow * n);
        gl_FragColor = vec4(col, 1.0);
    }
  `,
    waves: `
    precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec3 u_baseColor;
    uniform vec3 u_accentColor;
    varying vec2 v_texCoord;

    void main() {
        vec2 uv = v_texCoord;
        
        float wave1 = sin(uv.x * 3.0 + u_time * 0.4) * 0.15;
        float wave2 = sin(uv.x * 7.0 - u_time * 0.2) * 0.05;
        float y = uv.y + wave1 + wave2;
        
        float line = smoothstep(0.02, 0.0, abs(y - 0.5));
        float line2 = smoothstep(0.04, 0.0, abs(y - 0.3)) * 0.3;
        float line3 = smoothstep(0.04, 0.0, abs(y - 0.7)) * 0.3;
        
        float intensity = line + line2 + line3;
        vec3 col = mix(u_baseColor, u_accentColor, intensity * 0.6);
        gl_FragColor = vec4(col, 1.0);
    }
  `,
    nexus: `
    precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec3 u_baseColor;
    uniform vec3 u_accentColor;
    varying vec2 v_texCoord;

    void main() {
        vec2 uv = v_texCoord;
        uv.x *= u_resolution.x / u_resolution.y;
        
        vec2 grid = fract(uv * 8.0 + u_time * 0.05) - 0.5;
        float lines = smoothstep(0.03, 0.01, abs(grid.x)) + smoothstep(0.03, 0.01, abs(grid.y));
        
        float intersections = smoothstep(0.15, 0.0, length(grid)) * (sin(u_time * 1.5) * 0.5 + 0.5);
        
        vec3 col = mix(u_baseColor, u_accentColor, min(1.0, lines * 0.15 + intersections));
        gl_FragColor = vec4(col, 1.0);
    }
  `,
    cosmic: `
    precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec3 u_baseColor;
    uniform vec3 u_accentColor;
    varying vec2 v_texCoord;

    float random(vec2 st) {
        return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
    }

    void main() {
        vec2 uv = v_texCoord;
        uv.x *= u_resolution.x / u_resolution.y;
        
        vec2 g = floor(uv * 120.0);
        vec2 f = fract(uv * 120.0) - 0.5;
        float n = random(g);
        float star = smoothstep(0.3, 0.1, length(f)) * step(0.97, n);
        
        star *= sin(u_time * 1.5 + n * 20.0) * 0.5 + 0.5;
        
        float nebula = sin(uv.x * 1.5 + u_time * 0.05) * cos(uv.y * 2.0 + u_time * 0.08);
        nebula = nebula * 0.5 + 0.5;
        
        vec3 col = mix(u_baseColor, u_accentColor, star + nebula * 0.15);
        gl_FragColor = vec4(col, 1.0);
    }
  `,
    emerald_tide: `
    precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec3 u_baseColor;
    uniform vec3 u_accentColor;
    varying vec2 v_texCoord;

    float random(vec2 st) {
        return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
    }

    void main() {
        vec2 uv = v_texCoord;
        // Fix aspect ratio so dots aren't stretched
        uv.x *= u_resolution.x / u_resolution.y;
        float size = 55.0;
        
        // Wave distortion
        float wave = sin(uv.x * 4.0 + u_time * 0.1) * 0.015;
        uv.y += wave;
        
        vec2 g = floor(uv * size);
        vec2 f = fract(uv * size) - 0.5;
        
        float n = random(g);
        float d = length(f);
        float glow = smoothstep(0.2, 0.0, d);
        
        // Palette: Deep Forest & Oxidized Patina
        vec3 forest = vec3(0.02, 0.1, 0.08);
        vec3 patina = vec3(0.4, 0.8, 0.7);
        
        vec3 col = mix(vec3(0.01), mix(forest, patina, n), glow * (0.3 + 0.7 * sin(u_time * 0.1 + n * 3.0)));
        gl_FragColor = vec4(col, 1.0);
    }
  `,
    royal_bronze: `
    precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec3 u_baseColor;
    uniform vec3 u_accentColor;
    varying vec2 v_texCoord;

    float random(vec2 st) {
        return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
    }

    void main() {
        vec2 uv = v_texCoord;
        // Fix aspect ratio so dots aren't stretched
        uv.x *= u_resolution.x / u_resolution.y;
        
        // Increased from 40.0 to 120.0 to create an intricate woven texture
        float size = 120.0;
        
        // Staggered grid logic to create the "weave" pattern
        if(mod(floor(uv.y * size), 2.0) == 0.0) {
            uv.x += 0.5 / size;
        }
        
        vec2 g = floor(uv * size);
        vec2 f = fract(uv * size) - 0.5;
        
        float n = random(g);
        float d = length(f);
        
        // Subtle, slow shimmer effect
        float shimmer = 0.5 + 0.5 * sin(u_time * 0.08 + n * 6.28);
        float point = smoothstep(0.25, 0.05, d);
        
        // Palette: Midnight & Burnished Royal Bronze
        vec3 midnight = vec3(0.02, 0.02, 0.04);
        vec3 bronze = vec3(0.6, 0.45, 0.2);
        
        // Mix the base and accent based on the point shape, randomness, and shimmer
        vec3 col = mix(midnight, bronze, point * n * shimmer);
        
        gl_FragColor = vec4(col, 1.0);
    }
  `,
    css_emerald: `
    precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform float u_pixelRatio;
    uniform vec3 u_baseColor;
    uniform vec3 u_accentColor;
    varying vec2 v_texCoord;

    float random(vec2 st) {
        return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
    }

    void main() {
        vec2 uv = v_texCoord;
        uv.x *= u_resolution.x / u_resolution.y;
        
        // The original CSS was a simple, straight un-staggered grid with 24px logical spacing
        float pr = u_pixelRatio > 0.0 ? u_pixelRatio : 1.5;
        float size = u_resolution.y / (24.0 * pr); 
        
        vec2 g = floor(uv * size);
        vec2 f = fract(uv * size) - 0.5;
        
        float n = random(g);
        float d = length(f);
        
        // The discreet per-dot shimmer from Royal Bronze
        float shimmer = 0.5 + 0.5 * sin(u_time * 1.5 + n * 6.28);
        
        // Very sharp, small dot (approx 1-2px) to match original CSS grid perfectly
        float radius = 1.0 / 24.0;
        float point = smoothstep(radius + 0.01, radius - 0.01, d);
        
        // Colors from Emerald theme (slightly emerald bg, bright emerald dots)
        vec3 bg = vec3(0.03, 0.07, 0.05); // Slightly more emerald dark background
        vec3 dotColor = vec3(0.1, 0.8, 0.45); // Bright emerald green
        
        // Ensure dots never permanently vanish. We mix by point * intensity
        // removing the '* n' which permanently hid random dots.
        float intensity = 0.4 + 0.6 * shimmer;
        vec3 col = mix(bg, dotColor, point * intensity);
        
        gl_FragColor = vec4(col, 1.0);
    }
  `,
};

export type ShaderVariant = keyof typeof SHADERS;

const vertexShaderSource = `
  attribute vec2 a_position;
  varying vec2 v_texCoord;
  void main() {
    v_texCoord = a_position * 0.5 + 0.5; 
    gl_Position = vec4(a_position, 0.0, 1.0);
  }
`;

export interface ShaderBackgroundProps {
    /** RGB values from 0.0 to 1.0 */
    baseColor?: [number, number, number];
    /** RGB values from 0.0 to 1.0 */
    accentColor?: [number, number, number];
    variant?: ShaderVariant;
}

export function ShaderBackground({
    baseColor = [0.02, 0.05, 0.04],
    accentColor = [0.85, 0.75, 0.45],
    variant = 'pointillism',
}: ShaderBackgroundProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        let gl = canvas.getContext('webgl');
        if (!gl) return;

        let animationFrameId: number;
        let program: WebGLProgram | null = null;
        let vertexShader: WebGLShader | null = null;
        let fragmentShader: WebGLShader | null = null;
        let positionBuffer: WebGLBuffer | null = null;
        let isContextLost = false;

        const compileShader = (type: number, source: string) => {
            if (!gl) return null;
            const shader = gl.createShader(type);
            if (!shader) return null;
            gl.shaderSource(shader, source);
            gl.compileShader(shader);
            if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
                console.error('Shader compile error:', gl.getShaderInfoLog(shader));
                gl.deleteShader(shader);
                return null;
            }
            return shader;
        };

        const initWebGL = () => {
            if (!gl) return false;

            vertexShader = compileShader(gl.VERTEX_SHADER, vertexShaderSource);
            const fragmentShaderSource = SHADERS[variant] || SHADERS.pointillism;
            fragmentShader = compileShader(gl.FRAGMENT_SHADER, fragmentShaderSource);
            if (!vertexShader || !fragmentShader) return false;

            program = gl.createProgram();
            if (!program) return false;

            gl.attachShader(program, vertexShader);
            gl.attachShader(program, fragmentShader);
            gl.linkProgram(program);

            if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
                console.error('Program link error:', gl.getProgramInfoLog(program));
                return false;
            }

            // biome-ignore lint/correctness/useHookAtTopLevel: This is a WebGL method, not a React Hook
            gl.useProgram(program);

            positionBuffer = gl.createBuffer();
            gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
            const positions = new Float32Array([
                -1.0, -1.0, 1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, 1.0, 1.0,
            ]);
            gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

            const positionLocation = gl.getAttribLocation(program, 'a_position');
            gl.enableVertexAttribArray(positionLocation);
            gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

            return true;
        };

        let resizeCanvas = () => {};
        let startTime = performance.now();

        const render = (time: number) => {
            if (isContextLost || document.hidden || !gl || !program) {
                animationFrameId = requestAnimationFrame(render);
                return;
            }

            const uTime = (time - startTime) * 0.001;

            const timeLocation = gl.getUniformLocation(program, 'u_time');
            const baseColorLocation = gl.getUniformLocation(program, 'u_baseColor');
            const accentColorLocation = gl.getUniformLocation(program, 'u_accentColor');

            gl.uniform1f(timeLocation, uTime);
            gl.uniform3f(baseColorLocation, baseColor[0], baseColor[1], baseColor[2]);
            gl.uniform3f(accentColorLocation, accentColor[0], accentColor[1], accentColor[2]);

            gl.drawArrays(gl.TRIANGLES, 0, 6);

            animationFrameId = requestAnimationFrame(render);
        };

        const startRendering = () => {
            if (initWebGL()) {
                if (!gl || !program) return;
                const resolutionLocation = gl.getUniformLocation(program, 'u_resolution');
                const pixelRatioLocation = gl.getUniformLocation(program, 'u_pixelRatio');

                resizeCanvas = () => {
                    if (!canvas || !gl || !program) return;
                    const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
                    canvas.width = window.innerWidth * pixelRatio;
                    canvas.height = window.innerHeight * pixelRatio;
                    gl.viewport(0, 0, canvas.width, canvas.height);

                    // biome-ignore lint/correctness/useHookAtTopLevel: This is a WebGL method, not a React Hook
                    gl.useProgram(program);
                    gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
                    gl.uniform1f(pixelRatioLocation, pixelRatio);
                };

                window.addEventListener('resize', resizeCanvas);
                resizeCanvas();

                startTime = performance.now();
                animationFrameId = requestAnimationFrame(render);
            }
        };

        const cleanupWebGL = () => {
            if (!gl) return;
            if (program) gl.deleteProgram(program);
            if (vertexShader) gl.deleteShader(vertexShader);
            if (fragmentShader) gl.deleteShader(fragmentShader);
            if (positionBuffer) gl.deleteBuffer(positionBuffer);
        };

        startRendering();

        const handleVisibilityChange = () => {
            if (!document.hidden) {
                startTime = performance.now() - (performance.now() - startTime);
            }
        };
        document.addEventListener('visibilitychange', handleVisibilityChange);

        const handleContextLost = (e: Event) => {
            e.preventDefault();
            isContextLost = true;
            cancelAnimationFrame(animationFrameId);
        };

        const handleContextRestored = () => {
            isContextLost = false;
            gl = canvas.getContext('webgl');
            cleanupWebGL();
            startRendering();
        };

        canvas.addEventListener('webglcontextlost', handleContextLost);
        canvas.addEventListener('webglcontextrestored', handleContextRestored);

        return () => {
            window.removeEventListener('resize', resizeCanvas);
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            canvas.removeEventListener('webglcontextlost', handleContextLost);
            canvas.removeEventListener('webglcontextrestored', handleContextRestored);
            cancelAnimationFrame(animationFrameId);
            cleanupWebGL();
        };
    }, [baseColor, accentColor, variant]); // Add variant to dependency array

    return (
        <canvas
            ref={canvasRef}
            className="fixed inset-0 -z-10 pointer-events-none w-screen h-screen"
        />
    );
}
