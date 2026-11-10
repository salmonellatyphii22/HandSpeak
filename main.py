
import cv2
import mediapipe as mp
import time
import threading
from collections import deque


class GestureCamera:

    def __init__(self):
        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.previous_time = time.time()

        # Gesture information
        self.history = deque(maxlen=8)
        self.current_gesture = "NO GESTURE"
        self.hand_count = 0
        self.fps = 0
        self.camera_active = False
        self.camera_error = None

        self.last_gesture = ""
        self.last_detection_time = 0

        # Thread synchronization
        self.lock = threading.Lock()
        self.stream_lock = threading.Lock()

        # Gesture configuration
        self.finger_tips = [8, 12, 16, 20]
        self.thumb_tip = 4

    # ==========================================
    # GESTURE HISTORY
    # ==========================================

    def add_detection(self, gesture):

        now = time.time()

        if (
            gesture != self.last_gesture
            or now - self.last_detection_time > 1.5
        ):
            with self.lock:
                self.history.appendleft({
                    "time": time.strftime("%H:%M:%S"),
                    "gesture": gesture
                })

            self.last_gesture = gesture
            self.last_detection_time = now

    # ==========================================
    # GESTURE DETECTION
    # ==========================================

    def detect_gesture(self, lm_list):

        finger_fold_status = []

        for tip in self.finger_tips:
            finger_fold_status.append(
                lm_list[tip].x < lm_list[tip - 3].x
            )

        thumb_tip = self.thumb_tip

        thumb_x = lm_list[thumb_tip].x
        thumb_y = lm_list[thumb_tip].y

        index_x = lm_list[8].x
        index_y = lm_list[8].y

        gesture = "NO GESTURE"

        # LIKE
        if (
            lm_list[4].y < lm_list[3].y < lm_list[2].y
            and all(finger_fold_status)
        ):
            gesture = "LIKE"

        # DISLIKE
        if (
            lm_list[4].y > lm_list[3].y > lm_list[2].y
            and all(finger_fold_status)
        ):
            gesture = "DISLIKE"

        # OK
        distance = (
            (thumb_x - index_x) ** 2
            + (thumb_y - index_y) ** 2
        ) ** 0.5

        if distance < 0.05:
            if (
                not finger_fold_status[1]
                and not finger_fold_status[2]
                and not finger_fold_status[3]
            ):
                gesture = "OK"

        # PEACE
        ring_x = lm_list[16].x
        ring_y = lm_list[16].y

        pinky_x = lm_list[20].x
        pinky_y = lm_list[20].y

        distance_thumb_ring = (
            (thumb_x - ring_x) ** 2
            + (thumb_y - ring_y) ** 2
        ) ** 0.5

        distance_ring_pinky = (
            (ring_x - pinky_x) ** 2
            + (ring_y - pinky_y) ** 2
        ) ** 0.5

        if (
            distance_thumb_ring < 0.05
            and distance_ring_pinky < 0.05
            and not finger_fold_status[0]
            and not finger_fold_status[1]
        ):
            gesture = "PEACE"

        # CALL ME
        if (
            finger_fold_status[0]
            and finger_fold_status[1]
            and finger_fold_status[3]
        ):
            distance_thumb_pinky = (
                (thumb_x - pinky_x) ** 2
                + (thumb_y - pinky_y) ** 2
            ) ** 0.5

            if distance_thumb_pinky > 0.4:
                gesture = "CALL ME"

        # STOP
        if (
            lm_list[4].y < lm_list[3].y < lm_list[2].y
            and lm_list[8].y < lm_list[6].y < lm_list[5].y
            and lm_list[12].y < lm_list[10].y < lm_list[9].y
            and lm_list[16].y < lm_list[14].y < lm_list[13].y
            and lm_list[20].y < lm_list[18].y < lm_list[17].y
        ):
            gesture = "STOP"

        # FORWARD
        if (
            lm_list[8].y < lm_list[6].y < lm_list[5].y
            and lm_list[12].y > lm_list[11].y > lm_list[10].y
            and lm_list[16].y > lm_list[15].y > lm_list[14].y
            and lm_list[20].y > lm_list[19].y > lm_list[18].y
            and lm_list[4].x > lm_list[3].x
        ):
            gesture = "FORWARD"

        # LEFT
        if (
            lm_list[4].y < lm_list[2].y
            and lm_list[8].x < lm_list[6].x
            and lm_list[12].x > lm_list[10].x
            and lm_list[16].x > lm_list[14].x
            and lm_list[20].x > lm_list[18].x
            and lm_list[5].x < lm_list[0].x
        ):
            gesture = "LEFT"

        # RIGHT
        if (
            lm_list[4].y < lm_list[2].y
            and lm_list[8].x > lm_list[6].x
            and lm_list[12].x < lm_list[10].x
            and lm_list[16].x < lm_list[14].x
            and lm_list[20].x < lm_list[18].x
        ):
            gesture = "RIGHT"

        # I LOVE YOU
        if (
            lm_list[8].y < lm_list[6].y < lm_list[5].y
            and lm_list[12].y > lm_list[11].y > lm_list[10].y
            and lm_list[16].y > lm_list[15].y > lm_list[14].y
            and lm_list[20].y < lm_list[19].y < lm_list[18].y
            and lm_list[4].x > lm_list[3].x
        ):
            gesture = "I LOVE YOU"

        return gesture

    # ==========================================
    # DASHBOARD STATISTICS
    # ==========================================

        # ==========================================
    # PROCESS BROWSER CAMERA FRAME
    # ==========================================

    def process_frame(self, frame):

        try:
            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (960, 540))

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            results = self.hands.process(rgb)

            detected_gesture = "NO GESTURE"
            hand_count = 0

            # Hand detection
            if results.multi_hand_landmarks:

                hand_count = len(
                    results.multi_hand_landmarks
                )

                for hand_landmarks in results.multi_hand_landmarks:

                    lm_list = hand_landmarks.landmark

                    hand_gesture = self.detect_gesture(
                        lm_list
                    )

                    if (
                        detected_gesture == "NO GESTURE"
                        and hand_gesture != "NO GESTURE"
                    ):
                        detected_gesture = hand_gesture

                    self.mp_draw.draw_landmarks(
                        frame,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS
                    )

            # FPS
            current_time = time.time()

            fps = 1 / max(
                current_time - self.previous_time,
                0.001
            )

            self.previous_time = current_time

            # Update history
            if detected_gesture != "NO GESTURE":
                self.add_detection(
                    detected_gesture
                )

            # Update statistics
            with self.lock:

                self.current_gesture = (
                    detected_gesture
                )

                self.hand_count = hand_count

                self.fps = fps

                self.camera_active = True

                self.camera_error = None

            # Overlay
            cv2.rectangle(
                frame,
                (0, 0),
                (960, 55),
                (28, 20, 42),
                -1
            )

            cv2.putText(
                frame,
                "HANDSPEAK | LIVE DETECTION",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (220, 190, 255),
                2
            )

            cv2.putText(
                frame,
                detected_gesture,
                (25, 505),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (170, 255, 190),
                2
            )

            # Encode processed frame
            success, buffer = cv2.imencode(
                ".jpg",
                frame,
                [
                    cv2.IMWRITE_JPEG_QUALITY,
                    85
                ]
            )

            if not success:
                return None

            return buffer.tobytes()

        except Exception as error:

            with self.lock:
                self.camera_error = str(error)
                self.camera_active = False

            return None

    # ==========================================
    # DASHBOARD STATISTICS
    # ==========================================

    def get_stats(self):

        with self.lock:

            return {
                "gesture": self.current_gesture,
                "hands": self.hand_count,
                "fps": round(self.fps, 1),
                "active": self.camera_active,
                "error": self.camera_error,
                "history": list(self.history)
            }