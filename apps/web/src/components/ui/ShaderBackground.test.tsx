import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ShaderBackground } from './ShaderBackground';

describe('ShaderBackground', () => {
    it('should render a canvas with the correct Tailwind classes and request a WebGL context', () => {
        // Mock getContext to track if 'webgl' is requested and prevent errors
        const getContextMock = vi.fn().mockReturnValue({
            createShader: vi.fn(),
            shaderSource: vi.fn(),
            compileShader: vi.fn(),
            getShaderParameter: vi.fn().mockReturnValue(true),
            createProgram: vi.fn(),
            attachShader: vi.fn(),
            linkProgram: vi.fn(),
            getProgramParameter: vi.fn().mockReturnValue(true),
            useProgram: vi.fn(),
            createBuffer: vi.fn(),
            bindBuffer: vi.fn(),
            bufferData: vi.fn(),
            getAttribLocation: vi.fn().mockReturnValue(0),
            enableVertexAttribArray: vi.fn(),
            vertexAttribPointer: vi.fn(),
            getUniformLocation: vi.fn().mockReturnValue(0),
            viewport: vi.fn(),
            uniform2f: vi.fn(),
            uniform1f: vi.fn(),
            uniform3f: vi.fn(),
            drawArrays: vi.fn(),
            deleteProgram: vi.fn(),
            deleteShader: vi.fn(),
            deleteBuffer: vi.fn(),
        });

        HTMLCanvasElement.prototype.getContext =
            getContextMock as unknown as typeof HTMLCanvasElement.prototype.getContext;

        // Mock window APIs
        vi.spyOn(window, 'requestAnimationFrame').mockImplementation(
            (cb) => setTimeout(() => cb(performance.now()), 0) as unknown as number,
        );
        vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((id) => clearTimeout(id));

        const { container, unmount } = render(<ShaderBackground />);

        const canvas = container.querySelector('canvas');
        expect(canvas).toBeInTheDocument();
        expect(canvas).toHaveClass('fixed inset-0 -z-10 pointer-events-none w-screen h-screen');

        expect(getContextMock).toHaveBeenCalledWith('webgl');

        unmount();
    });
});
