"""
Face ID Service using OpenCV LBPH.
Single model for all employees, stored as model.yml file.
"""
import os
import cv2
import numpy as np
import base64
from django.conf import settings


class FaceService:
    """
    OpenCV LBPH Face Recognition Service.
    - Single model.yml file for all employees
    - Each employee has a unique face_label (int)
    - Support for update() when adding new employees
    """
    
    MODEL_DIR = os.path.join(settings.MEDIA_ROOT, 'face_models')
    MODEL_PATH = os.path.join(MODEL_DIR, 'model.yml')
    
    # Confidence threshold - lower is better match
    CONFIDENCE_THRESHOLD = 80
    
    def __init__(self):
        self.cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    def _ensure_model_dir(self):
        """Create model directory if it doesn't exist."""
        os.makedirs(self.MODEL_DIR, exist_ok=True)
    
    def _load_model(self) -> bool:
        """Load existing LBPH model from file. Returns True if loaded."""
        if os.path.exists(self.MODEL_PATH):
            try:
                self.recognizer.read(self.MODEL_PATH)
                return True
            except Exception:
                return False
        return False
    
    def _save_model(self):
        """Save LBPH model to file."""
        self._ensure_model_dir()
        self.recognizer.write(self.MODEL_PATH)
    
    def _detect_faces(self, frame):
        """Detect faces in a frame. Returns list of (x, y, w, h) tuples."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(100, 100)
        )
        return gray, faces
    
    def _extract_face_rois(self, frames: list) -> list:
        """Extract normalized face ROIs from frames."""
        face_rois = []
        for frame in frames:
            gray, faces = self._detect_faces(frame)
            for (x, y, w, h) in faces:
                # Normalize to 200x200
                face_roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
                face_rois.append(face_roi)
        return face_rois
    
    def register_employee(self, face_label: int, frames: list) -> dict:
        """
        Register an employee's face with 10-30 snapshots.
        
        Args:
            face_label: Unique integer label for this employee
            frames: List of OpenCV frames (BGR images)
        
        Returns:
            dict with 'success', 'faces_count', 'message'
        """
        if not frames:
            return {
                'success': False,
                'faces_count': 0,
                'message': 'Hech qanday rasm berilmadi'
            }
        
        # Extract faces from frames
        faces = self._extract_face_rois(frames)
        
        if len(faces) < 10:
            return {
                'success': False,
                'faces_count': len(faces),
                'message': f'Kamida 10 ta yuz kerak (topildi: {len(faces)})'
            }
        
        # Limit to 30 faces
        faces = faces[:30]
        labels = np.array([face_label] * len(faces))
        
        # Load existing model and update, or train new
        if self._load_model():
            try:
                self.recognizer.update(faces, labels)
            except Exception:
                # If update fails, retrain
                self.recognizer.train(faces, labels)
        else:
            self.recognizer.train(faces, labels)
        
        self._save_model()
        
        return {
            'success': True,
            'faces_count': len(faces),
            'message': f'{len(faces)} ta yuz ro\'yxatga olindi'
        }
    
    def verify_face(self, frame) -> dict:
        """
        Verify a face against the trained model.
        
        Args:
            frame: OpenCV frame (BGR image)
        
        Returns:
            dict with 'success', 'face_label', 'confidence'
        """
        if not self._load_model():
            return {
                'success': False,
                'face_label': None,
                'confidence': 0.0,
                'message': 'Face model topilmadi'
            }
        
        gray, faces = self._detect_faces(frame)
        
        if len(faces) == 0:
            return {
                'success': False,
                'face_label': None,
                'confidence': 0.0,
                'message': 'Yuz aniqlanmadi'
            }
        
        # Use the first (largest) face
        x, y, w, h = faces[0]
        face_roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
        
        label, confidence = self.recognizer.predict(face_roi)
        
        if confidence < self.CONFIDENCE_THRESHOLD:
            return {
                'success': True,
                'face_label': int(label),
                'confidence': round(confidence, 2),
                'message': 'Yuz tasdiqlandi'
            }
        
        return {
            'success': False,
            'face_label': None,
            'confidence': round(confidence, 2),
            'message': 'Yuz tanilmadi'
        }
    
    @staticmethod
    def base64_to_frame(base64_str: str):
        """
        Convert base64 encoded image to OpenCV frame.
        Handles both raw base64 and data URL format.
        """
        if not base64_str:
            return None
        
        # Remove data URL prefix if present
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        
        try:
            img_bytes = base64.b64decode(base64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception:
            return None
    
    @staticmethod
    def frame_to_base64(frame) -> str:
        """Convert OpenCV frame to base64 string."""
        _, buffer = cv2.imencode('.jpg', frame)
        return base64.b64encode(buffer).decode('utf-8')
    
    def model_exists(self) -> bool:
        """Check if face model file exists."""
        return os.path.exists(self.MODEL_PATH)
    
    def delete_model(self):
        """Delete the face model file."""
        if os.path.exists(self.MODEL_PATH):
            os.remove(self.MODEL_PATH)
