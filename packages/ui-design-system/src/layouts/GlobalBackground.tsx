export function GlobalBackground() {
    return (
        <div className="fixed inset-0 z-[-1] pointer-events-none bg-boxel-canvas">
            {/* Subtle warm isometric/voxel grid matrix on Deep Forest Moss canvas */}
            <div
                className="absolute inset-0 opacity-20"
                style={{
                    backgroundImage:
                        'radial-gradient(rgba(242, 234, 211, 0.25) 1px, transparent 1px)',
                    backgroundSize: '20px 20px',
                }}
            />
        </div>
    );
}
