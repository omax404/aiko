
import os
import cv2
import logging
import numpy as np
import time
from pathlib import Path
from core.config_manager import config

logger = logging.getLogger("Biometrics")

class BiometricScanner:
    """
    Aiko's Biometric Security Layer.
    Uses OpenCV for Face Recognition and Master Identification.
    """
    def __init__(self):
        self.cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(self.cascade_path)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.data_dir = Path("data/biometrics")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.data_dir / "master_model.yml"
        self.training_dir = self.data_dir / "training"
        self.training_dir.mkdir(parents=True, exist_ok=True)
        
        self.is_trained = self.model_path.exists()
        if self.is_trained:
            self.recognizer.read(str(self.model_path))
            
    def register_master(self, camera_index=0, num_samples=30):
        """Captures training data from the webcam to register the Master."""
        logger.info("Initializing Master Registration sequence...")
        cap = cv2.VideoCapture(camera_index)
        count = 0
        
        while count < num_samples:
            ret, frame = cap.read()
            if not ret: break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            for (x, y, w, h) in faces:
                count += 1
                face_img = gray[y:y+h, x:x+w]
                cv2.imwrite(str(self.training_dir / f"master_{count}.jpg"), face_img)
                # Draw for visual feedback (internal use)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            if count % 5 == 0:
                logger.info(f"Bio-Sampling: {count}/{num_samples}")
            
            time.sleep(0.1)
            
        cap.release()
        self.train_model()
        return count >= num_samples

    def train_model(self):
        """Trains the LBPH recognizer on the captured samples."""
        faces = []
        ids = []
        
        for img_path in self.training_dir.glob("*.jpg"):
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            faces.append(img)
            ids.append(1) # ID 1 is always the Master
            
        if faces:
            self.recognizer.train(faces, np.array(ids))
            self.recognizer.save(str(self.model_path))
            self.is_trained = True
            logger.info("✅ Biometric Model trained and secured.")
            return True
        return False

    def scan_for_master(self, frame) -> tuple:
        """
        Scans a single frame for the Master.
        Returns (is_master, confidence, box)
        """
        if not self.is_trained:
            return False, 0.0, None
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            id, confidence = self.recognizer.predict(gray[y:y+h, x:x+w])
            
            # LBPH confidence: lower is better. 0 is perfect.
            # Usually < 50 is very good, < 70 is acceptable.
            if id == 1 and confidence < 75:
                return True, confidence, (x, y, w, h)
                
        return False, 0.0, None

    async def autonomous_scan(self, camera_index=0):
        """One-shot scan from camera to verify presence."""
        cap = cv2.VideoCapture(camera_index)
        ret, frame = cap.read()
        cap.release()
        
        if not ret: return False
        is_master, conf, _ = self.scan_for_master(frame)
        return is_master

# Singleton instance
biometrics = BiometricScanner()
