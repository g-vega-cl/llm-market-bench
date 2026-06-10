import { useEffect, useRef, useState } from 'react';

export function BackgroundVideo() {
    const [isMounted, setIsMounted] = useState(false);
    const videoRef = useRef<HTMLVideoElement>(null);

    // The permanent S3 URLs stripped of expiring tokens
    const videoUrl =
        'https://benchify-media.s3.us-west-2.amazonaws.com/Pointillism_background_with_shim%E2%80%A6_202606100818.mp4';
    const posterUrl =
        'https://benchify-media.s3.us-west-2.amazonaws.com/Pointillism_background_with_shim.webp';

    useEffect(() => {
        // 1. Tell React we have safely hydrated on the client
        setIsMounted(true);

        let ticking = false;

        // 2. High-performance scroll listener to move the camera
        const handleScroll = () => {
            if (!ticking && videoRef.current) {
                window.requestAnimationFrame(() => {
                    const scrollX = window.scrollX;
                    const scrollY = window.scrollY;

                    if (videoRef.current) {
                        // Move the video slightly for a parallax effect.
                        // scale(1.1) ensures the hard edges never peek into the screen.
                        videoRef.current.style.transform = `scale(1.1) translate3d(${-scrollX * 0.05}px, ${-scrollY * 0.05}px, 0)`;
                    }
                    ticking = false;
                });
                ticking = true;
            }
        };

        window.addEventListener('scroll', handleScroll, { passive: true });

        return () => {
            window.removeEventListener('scroll', handleScroll);
        };
    }, []);

    // -----------------------------------------------------------
    // SSR Phase: Return a fast-loading static image div
    // -----------------------------------------------------------
    if (!isMounted) {
        return (
            <div
                data-testid="background-video"
                style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100vw',
                    height: '100vh',
                    zIndex: -1,
                    backgroundImage: `url(${posterUrl})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundColor: 'transparent',
                }}
            />
        );
    }

    // -----------------------------------------------------------
    // CSR Phase: Inject the hardware-accelerated video
    // -----------------------------------------------------------
    return (
        <video
            data-testid="background-video"
            ref={videoRef}
            autoPlay
            loop
            muted
            playsInline
            preload="none" // CRITICAL: Prioritizes First Contentful Paint over video data
            poster={posterUrl}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '110vw', // Oversized to account for the scale and movement
                height: '110vh',
                objectFit: 'cover',
                zIndex: -1,
                willChange: 'transform', // Alerts GPU to expect movement
                transform: 'translate3d(0, 0, 0)',
            }}
        >
            <source src={videoUrl} type="video/mp4" />
        </video>
    );
}
