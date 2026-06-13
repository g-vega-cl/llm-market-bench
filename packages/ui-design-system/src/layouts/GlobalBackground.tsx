export function GlobalBackground() {
    return (
        <div className="fixed inset-0 z-[-1] pointer-events-none">
            {/* Ambient glowing orbs for depth */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(0,242,254,0.1),_transparent_40%)]" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,_rgba(74,222,128,0.07),_transparent_40%)]" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(246,224,94,0.05),_transparent_50%)]" />

            {/* Precise dot grid pattern */}
            <div
                className="absolute inset-0 opacity-40"
                style={{
                    backgroundImage:
                        'radial-gradient(rgba(255, 255, 255, 0.4) 1px, transparent 1px)',
                    backgroundSize: '24px 24px',
                }}
            />
        </div>
    );
}
