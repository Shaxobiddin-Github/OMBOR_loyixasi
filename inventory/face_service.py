"""
Face ID Service — OpenCV LBPH yuz tanish tizimi.

Arxitektura:
  - Har bir xodim ALOHIDA .yml faylda saqlanadi: face_models/{face_label}.yml
  - Bitta xodimni o'chirish boshqalarga ta'sir qilmaydi
  - Verify: barcha modellarni yuklaydi, eng yaxshi moslikni topadi

Xususiyatlar:
  - LBPH (Local Binary Pattern Histogram) — oflayn, bepul
  - Histogram equalization — yorug'likka sezgirlikni kamaytiradi
  - Eng katta yuzni tanlash — orqa fondagi odamlarni e'tiborsiz qoldiradi
  - File locking — ko'p oqimli (multithreaded) Django uchun xavfsiz
  - Confidence foizga o'giriladi (0-100%, yuqori = yaxshiroq)

Texnik cheklovlar:
  - Faqat opencv-python, numpy, standart kutubxonalar
  - 100% oflayn, tashqi API yo'q
"""

import os
import glob
import base64
import threading
import logging

import cv2
import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════
# Modul darajasidagi fayl qulfi (file lock)
# ════════════════════════════════════════════════════════════════
# Django bir nechta threadlarda ishlaydi. Ikki jarayon bir vaqtda
# yozsa, fayl buzilib qolishi mumkin. threading.Lock() navbat ta'minlaydi.
_model_lock = threading.Lock()


class FaceService:
    """
    OpenCV LBPH yuz tanish xizmati.

    Fayl tuzilishi:
        media/face_models/
        ├── 1.yml    ← 1-xodim modeli
        ├── 2.yml    ← 2-xodim modeli
        └── 5.yml    ← 5-xodim modeli

    Ishlatilishi:
        service = FaceService()

        # Ro'yxatga olish (10-30 ta kadr)
        result = service.register_employee(face_label=1, frames=[...])

        # Tekshirish (1 ta kadr)
        result = service.verify_face(frame)
        # → {'success': True, 'face_label': 1, 'confidence': 87.5, ...}

        # Bitta xodim ma'lumotini o'chirish
        service.delete_employee_model(face_label=1)
    """

    MODEL_DIR = os.path.join(settings.MEDIA_ROOT, 'face_models')

    # ── Ishonchlilik chegarasi ──
    # LBPH confidence: 0 = mukammal mos, yuqori = yomonroq.
    # 60 dan past bo'lsa = tanildi, 60 dan oshsa = tanilmadi.
    CONFIDENCE_THRESHOLD = 54

    # Yuz tanish uchun standart o'lcham (normalize)
    FACE_SIZE = (200, 200)

    # Cascade classifier (bir marta yuklanadi, barcha instancelar uchun)
    _cascade = None

    def __init__(self):
        # Cascade classifier — lazy load (bir marta)
        if FaceService._cascade is None:
            FaceService._cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        self.cascade = FaceService._cascade

    # ════════════════════════════════════════════════════════════
    # Fayl yo'llari
    # ════════════════════════════════════════════════════════════

    def _ensure_model_dir(self):
        """Model katalogini yaratish (agar mavjud bo'lmasa)."""
        os.makedirs(self.MODEL_DIR, exist_ok=True)

    def _model_path(self, face_label: int) -> str:
        """Xodimning individual model fayl yo'li: face_models/{face_label}.yml"""
        return os.path.join(self.MODEL_DIR, f'{face_label}.yml')

    # ════════════════════════════════════════════════════════════
    # Cache (Singleton)
    # ════════════════════════════════════════════════════════════
    _models_cache = None
    _last_cache_update = None

    # ════════════════════════════════════════════════════════════
    # Fayl bilan ishlash (File I/O + Lock)
    # ════════════════════════════════════════════════════════════

    def _get_cache_key(self):
        """Cache haqiqiyligini tekshirish uchun papka o'zgarish vaqtini olish."""
        if not os.path.exists(self.MODEL_DIR):
            return 0
        return os.path.getmtime(self.MODEL_DIR)

    def _load_single_model(self, face_label: int):
        """
        Bitta xodim modelini yuklash.
        Returns: recognizer yoki None
        """
        path = self._model_path(face_label)
        if not os.path.exists(path):
            return None
        try:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(path)
            return recognizer
        except Exception as e:
            logger.warning(f"Model yuklashda xato (label={face_label}): {e}")
            return None

    def _load_all_models(self) -> list:
        """
        Barcha xodim modellarini yuklash (Cache bilan).
        Returns: [(face_label, recognizer), ...] ro'yxati
        """
        current_mtime = self._get_cache_key()

        # Agar cache mavjud va papka o'zgarmagan bo'lsa -> Cache dan qaytarish
        if (FaceService._models_cache is not None and 
            FaceService._last_cache_update == current_mtime):
            return FaceService._models_cache

        models = []
        if not os.path.isdir(self.MODEL_DIR):
            return models

        with _model_lock:
            # Double check locking ichida (balki boshqa thread yangilagandir)
            if (FaceService._models_cache is not None and 
                FaceService._last_cache_update == current_mtime):
                return FaceService._models_cache

            logger.info("Face modellarni diskdan qayta yuklash...")
            for filepath in glob.glob(os.path.join(self.MODEL_DIR, '*.yml')):
                filename = os.path.basename(filepath)
                try:
                    face_label = int(filename.replace('.yml', ''))
                except ValueError:
                    continue  # model.yml yoki boshqa fayllarni o'tkazib yuborish

                try:
                    recognizer = cv2.face.LBPHFaceRecognizer_create()
                    recognizer.read(filepath)
                    models.append((face_label, recognizer))
                except Exception as e:
                    logger.warning(f"Model yuklashda xato ({filename}): {e}")
            
            # Cache yangilash
            FaceService._models_cache = models
            FaceService._last_cache_update = current_mtime
            
        return models

    def _save_model(self, face_label: int, recognizer):
        """
        Xodim modelini faylga saqlash.
        Thread-safe: _model_lock bilan himoyalangan.
        Atomic write: avval .tmp ga yozadi, keyin rename qiladi.
        """
        self._ensure_model_dir()
        target_path = self._model_path(face_label)
        tmp_path = target_path + '.tmp'

        with _model_lock:
            try:
                recognizer.write(tmp_path)
                # Atomic replace (works on both Linux and Windows)
                os.replace(tmp_path, target_path)
                
                # Cache invalidation (papka timestamp o'zgaradi, lekin aniqlik uchun reset qilamiz)
                FaceService._last_cache_update = None
                
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

    # ════════════════════════════════════════════════════════════
    # Yuz aniqlash va qayta ishlash (Detection + Preprocessing)
    # ════════════════════════════════════════════════════════════

    def _preprocess_gray(self, frame):
        """
        Kadrni kulrang tasvirga o'tkazib, histogram equalization qilish.

        Histogram equalization (cv2.equalizeHist) — piksellar intensivligini
        to'liq diapazon bo'ylab taqsimlaydi. Natija:
          - Qorong'u xonada ham yuz aniq ko'rinadi
          - Oynadan tushadigan yorug'lik ta'sir qilmaydi
          - Kontrastni oshiradi
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        equalized = cv2.equalizeHist(gray)
        return equalized

    def _detect_faces(self, frame):
        """
        Kadrdagi yuzlarni aniqlash.
        Returns: (equalized_gray, faces) — kulrang tasvir va yuzlar ro'yxati
        """
        equalized = self._preprocess_gray(frame)
        faces = self.cascade.detectMultiScale(
            equalized,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(100, 100)
        )
        return equalized, faces

    def _select_best_face(self, faces, frame_shape):
        """
        Eng yaxshi yuzni tanlash — eng katta yuz (w * h bo'yicha).
        Kameraga yaqin odam kattaroq ko'rinadi, orqa fondagi kichikroq.
        """
        if len(faces) == 0:
            return None
        if len(faces) == 1:
            return tuple(faces[0])
        # Eng katta maydonli yuz
        best = max(faces, key=lambda f: f[2] * f[3])
        return tuple(best)

    def _extract_face_roi(self, equalized_gray, x, y, w, h):
        """Bitta yuz ROI ni kesib, 200x200 ga normalize qilish."""
        face_roi = equalized_gray[y:y + h, x:x + w]
        return cv2.resize(face_roi, self.FACE_SIZE)

    def _extract_all_face_rois(self, frames: list) -> list:
        """
        Bir nechta kadrlardan yuz ROI larini ajratib olish.
        Har bir kadrdan eng katta yuzni tanlaydi.
        """
        rois = []
        for frame in frames:
            equalized, faces = self._detect_faces(frame)
            best = self._select_best_face(faces, frame.shape)
            if best is not None:
                x, y, w, h = best
                roi = self._extract_face_roi(equalized, x, y, w, h)
                rois.append(roi)
        return rois

    # ════════════════════════════════════════════════════════════
    # Confidence konvertatsiyasi
    # ════════════════════════════════════════════════════════════

    def _confidence_to_percent(self, raw_confidence: float) -> float:
        """
        LBPH confidence ni foizga (0-100%) o'girish.
          - raw = 0   → 100% (mukammal)
          - raw = 54  → 0% (chegara)
          - raw > 54  → 0% (tanilmadi)
        """
        if raw_confidence <= 0:
            return 100.0
        percent = max(0.0, (1.0 - raw_confidence / self.CONFIDENCE_THRESHOLD)) * 100.0
        return round(percent, 1)

    # ════════════════════════════════════════════════════════════
    # Asosiy metodlar
    # ════════════════════════════════════════════════════════════

    def register_employee(self, face_label: int, frames: list) -> dict:
        """
        Xodim yuzini ro'yxatga olish (10-30 ta kadr kerak).
        Har bir xodim alohida {face_label}.yml faylda saqlanadi.

        Args:
            face_label: Xodimning noyob raqamli belgisi (int)
            frames: OpenCV kadrlar ro'yxati (BGR)

        Returns:
            {'success': bool, 'faces_count': int, 'message': str}
        """
        if not frames:
            return {
                'success': False,
                'faces_count': 0,
                'message': 'Hech qanday rasm berilmadi'
            }

        # Barcha kadrlardan yuz ROI larini olish
        faces = self._extract_all_face_rois(frames)

        if len(faces) < 10:
            return {
                'success': False,
                'faces_count': len(faces),
                'message': f'Kamida 10 ta yuz kerak (topildi: {len(faces)})'
            }

        # Eng ko'pi 30 ta
        faces = faces[:30]
        # LBPH uchun label — hamma bir xil (chunki bu alohida model)
        labels = np.array([face_label] * len(faces))

        # Yangi recognizer yaratib, o'rgatamiz
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, labels)

        # Alohida faylga saqlash
        self._save_model(face_label, recognizer)

        return {
            'success': True,
            'faces_count': len(faces),
            'message': f'{len(faces)} ta yuz ro\'yxatga olindi'
        }

    def verify_face(self, frame) -> dict:
        """
        Yuzni BARCHA xodimlar modellariga solishtirish.

        Jarayon:
          1. Kadrdagi eng katta yuzni aniqlash
          2. Histogram equalization + normalize
          3. Barcha {label}.yml modellarni yuklash
          4. Har biriga predict qilish
          5. Eng past raw confidence (eng yaxshi moslik) ni tanlash
          6. Threshold tekshiruvi va foizga o'girish

        Args:
            frame: OpenCV kadri (BGR)

        Returns:
            {'success': bool, 'face_label': int|None, 'confidence': float, 'message': str}
        """
        # 1. Barcha modellarni yuklash
        models = self._load_all_models()
        if not models:
            return {
                'success': False,
                'face_label': None,
                'confidence': 0.0,
                'message': 'Face model topilmadi — xodimlar ro\'yxatga olinmagan'
            }

        # 2. Yuzni aniqlash
        equalized, faces = self._detect_faces(frame)
        if len(faces) == 0:
            return {
                'success': False,
                'face_label': None,
                'confidence': 0.0,
                'message': 'Yuz aniqlanmadi'
            }

        # 3. Eng katta yuzni tanlash
        best = self._select_best_face(faces, frame.shape)
        if best is None:
            return {
                'success': False,
                'face_label': None,
                'confidence': 0.0,
                'message': 'Yuz aniqlanmadi'
            }

        x, y, w, h = best
        face_roi = self._extract_face_roi(equalized, x, y, w, h)

        # 4. Har bir modelga predict qilish, eng yaxshi moslikni topish
        best_label = None
        best_raw = float('inf')  # Eng past raw = eng yaxshi

        for face_label, recognizer in models:
            try:
                predicted_label, raw_confidence = recognizer.predict(face_roi)
                if raw_confidence < best_raw:
                    best_raw = raw_confidence
                    best_label = face_label
            except Exception as e:
                logger.warning(f"Predict xatosi (label={face_label}): {e}")

        # 5. Threshold tekshiruvi
        logger.debug(f"Face ID: Label={best_label}, Raw={best_raw}, Threshold={self.CONFIDENCE_THRESHOLD}")

        if best_label is not None and best_raw < self.CONFIDENCE_THRESHOLD:
            logger.debug("Face ID: ACCEPTED")
            percent = self._confidence_to_percent(best_raw)
            return {
                'success': True,
                'face_label': best_label,
                'confidence': percent,
                'message': f'Yuz tasdiqlandi ({percent}%)'
            }
        
        logger.debug("Face ID: REJECTED (Distance too high)")

        percent = self._confidence_to_percent(best_raw) if best_raw != float('inf') else 0.0
        return {
            'success': False,
            'face_label': None,
            'confidence': percent,
            'message': f"Yuz o'xshashligi yetarli emas (Moslik: {percent}%). Qayta urinib ko'ring."
        }

    # ════════════════════════════════════════════════════════════
    # Model boshqaruvi (CRUD)
    # ════════════════════════════════════════════════════════════

    def delete_employee_model(self, face_label: int) -> bool:
        """
        Bitta xodimning face modelini o'chirish.
        Boshqa xodimlarga ta'sir qilmaydi!

        Args:
            face_label: o'chiriladigan xodimning face_label raqami

        Returns:
            True agar o'chirilgan bo'lsa, False agar fayl topilmasa
        """
        path = self._model_path(face_label)
        with _model_lock:
            if os.path.exists(path):
                os.remove(path)
                # Cache invalidation
                FaceService._last_cache_update = None
                logger.info(f"Face model o'chirildi: {path}")
                return True
        return False

    def delete_model(self):
        """
        BARCHA face modellarni o'chirish.
        Ehtiyotkorlik bilan ishlating!
        """
        with _model_lock:
            if os.path.isdir(self.MODEL_DIR):
                for filepath in glob.glob(os.path.join(self.MODEL_DIR, '*.yml')):
                    os.remove(filepath)
                # Cache invalidation
                FaceService._last_cache_update = None
                logger.info("Barcha face modellar o'chirildi")

    def model_exists(self) -> bool:
        """Kamida bitta face model fayli mavjudligini tekshirish."""
        if not os.path.isdir(self.MODEL_DIR):
            return False
        return len(glob.glob(os.path.join(self.MODEL_DIR, '*.yml'))) > 0

    def employee_model_exists(self, face_label: int) -> bool:
        """Bitta xodim uchun face model mavjudligini tekshirish."""
        return os.path.exists(self._model_path(face_label))

    def get_registered_labels(self) -> list:
        """Ro'yxatga olingan barcha face_label larni qaytarish."""
        labels = []
        if not os.path.isdir(self.MODEL_DIR):
            return labels
        for filepath in glob.glob(os.path.join(self.MODEL_DIR, '*.yml')):
            filename = os.path.basename(filepath)
            try:
                labels.append(int(filename.replace('.yml', '')))
            except ValueError:
                continue
        return sorted(labels)

    # ════════════════════════════════════════════════════════════
    # Yordamchi metodlar (Base64 konvertatsiya)
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def base64_to_frame(base64_str: str):
        """
        Base64 kodlangan tasvirni OpenCV kadriga o'girish.
        Data URL formatini ham qo'llab-quvvatlaydi.
        """
        if not base64_str:
            return None
        if ',' in base64_str:
            base64_str = base64_str.split(',', 1)[1]
        try:
            img_bytes = base64.b64decode(base64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception:
            return None

    @staticmethod
    def frame_to_base64(frame) -> str:
        """OpenCV kadrini base64 matnga o'girish."""
        _, buffer = cv2.imencode('.jpg', frame)
        return base64.b64encode(buffer).decode('utf-8')
