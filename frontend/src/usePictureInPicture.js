import { useEffect, useRef, useState } from "react";

export function usePictureInPicture({ onError } = {}) {
    const [pipTarget, setPipTarget] = useState(null);
    const windowRef = useRef(null);
    const openingRef = useRef(false);
    const generationRef = useRef(0);

    useEffect(() => () => {
        generationRef.current++;
        const pipWindow = windowRef.current;
        windowRef.current = null;
        pipWindow?.close();
    }, []);

    async function open() {
        if (!window.documentPictureInPicture) {
            onError?.("unsupported");
            return;
        }
        if (openingRef.current) return;

        openingRef.current = true;
        const generation = generationRef.current;
        try {
            if (windowRef.current && !windowRef.current.closed) {
                windowRef.current.focus();
                return;
            }
            const pipWindow = await window.documentPictureInPicture.requestWindow({
                width: 540,
                height: 240,
                disallowReturnToOpener: true,
            });
            // A pending request may complete after the component was unmounted.
            if (generation !== generationRef.current) {
                pipWindow.close();
                return;
            }
            windowRef.current = pipWindow;
            pipWindow.addEventListener("pagehide", () => {
                if (windowRef.current === pipWindow) {
                    windowRef.current = null;
                    setPipTarget(null);
                }
            }, { once: true });
            setPipTarget(pipWindow.document.body);
        } catch (error) {
            if (generation === generationRef.current) {
                console.error("Failed to open picture-in-picture:", error);
                onError?.("failed");
            }
        } finally {
            openingRef.current = false;
        }
    }

    return { pipTarget, open };
}
