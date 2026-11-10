document.addEventListener("DOMContentLoaded", () => {

    const gestureElement =
        document.getElementById("current-gesture");

    const gestureStat =
        document.getElementById("gesture-stat");

    const handCount =
        document.getElementById("hand-count");

    const fpsElement =
        document.getElementById("fps");

    const cameraStatus =
        document.getElementById("camera-status");

    const statusDot =
        document.getElementById("status-dot");

    const cameraError =
        document.getElementById("camera-error");

    const historyList =
        document.getElementById("history-list");

    const gestureDescription =
        document.getElementById("gesture-description");

    const cameraFeed =
        document.getElementById("camera-feed");

    const webcam =
        document.getElementById("webcam");

    const canvas =
        document.getElementById("camera-canvas");

    if (!gestureElement) return;

    const ctx =
        canvas.getContext("2d");

    const descriptions = {

        "LIKE":
            "A positive thumbs-up gesture detected.",

        "DISLIKE":
            "A thumbs-down gesture detected.",

        "OK":
            "The OK hand gesture was recognized.",

        "PEACE":
            "A peace sign gesture was recognized.",

        "CALL ME":
            "A call-me gesture was recognized.",

        "STOP":
            "A stop gesture was recognized.",

        "FORWARD":
            "A forward movement gesture was recognized.",

        "LEFT":
            "A left direction gesture was recognized.",

        "RIGHT":
            "A right direction gesture was recognized.",

        "I LOVE YOU":
            "The I Love You gesture was recognized.",

        "NO GESTURE":
            "Waiting for your next gesture..."
    };


    function updateHistory(history) {

        historyList.innerHTML = "";

        if (!history || history.length === 0) {

            historyList.innerHTML =
                '<p class="empty-state">' +
                'Your detected gestures will appear here.' +
                '</p>';

            return;
        }

        history.forEach(item => {

            const row =
                document.createElement("div");

            row.className =
                "history-item";

            const gesture =
                document.createElement("strong");

            gesture.textContent =
                item.gesture;

            const time =
                document.createElement("span");

            time.textContent =
                item.time;

            row.appendChild(gesture);
            row.appendChild(time);

            historyList.appendChild(row);
        });
    }


    function updateUI(data) {

        gestureElement.textContent =
            data.gesture;

        gestureStat.textContent =
            data.gesture;

        handCount.textContent =
            data.hands;

        fpsElement.textContent =
            data.fps;

        gestureDescription.textContent =
            descriptions[data.gesture]
            || "Gesture recognized.";

        updateHistory(data.history);

        cameraStatus.textContent =
            "Camera active";

        statusDot.classList.remove(
            "offline"
        );

        cameraError.style.display =
            "none";
    }


    async function startCamera() {

        try {

            const stream =
                await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: 960,
                        height: 540,
                        facingMode: "user"
                    },
                    audio: false
                });

            webcam.srcObject =
                stream;

            await webcam.play();

            cameraStatus.textContent =
                "Camera active";

            statusDot.classList.remove(
                "offline"
            );

            cameraError.style.display =
                "none";

            processFrames();

        } catch (error) {

            console.error(error);

            cameraStatus.textContent =
                "Camera unavailable";

            statusDot.classList.add(
                "offline"
            );

            cameraError.textContent =
                "Camera permission was denied or the camera is unavailable.";

            cameraError.style.display =
                "block";
        }
    }


    let processing = false;


    async function processFrames() {

        if (
            processing ||
            webcam.readyState < 2
        ) {
            requestAnimationFrame(
                processFrames
            );
            return;
        }

        processing = true;

        try {

            ctx.drawImage(
                webcam,
                0,
                0,
                canvas.width,
                canvas.height
            );

            const blob =
                await new Promise(resolve => {

                    canvas.toBlob(
                        resolve,
                        "image/jpeg",
                        0.75
                    );

                });

            const formData =
                new FormData();

            formData.append(
                "frame",
                blob,
                "frame.jpg"
            );

            const response =
                await fetch(
                    "/process_frame",
                    {
                        method: "POST",
                        body: formData
                    }
                );

            if (!response.ok) {
                throw new Error(
                    "Frame processing failed."
                );
            }

            const data =
                await response.json();

            updateUI(data);

            if (data.image) {

                cameraFeed.src =
                    "data:image/jpeg;base64," +
                    data.image;
            }

        } catch (error) {

            console.error(error);

            cameraStatus.textContent =
                "Processing error";

            statusDot.classList.add(
                "offline"
            );

        } finally {

            processing = false;

            setTimeout(
                () => requestAnimationFrame(
                    processFrames
                ),
                100
            );
        }
    }


    startCamera();

});