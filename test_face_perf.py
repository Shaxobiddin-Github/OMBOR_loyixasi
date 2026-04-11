import django
import os
import cv2
import time
import numpy as np

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from inventory.face_service import FaceService
from inventory.models import Employee

def test_performance():
    print("🚀 Face Service Performance Test")
    print("================================")
    
    service = FaceService()
    
    # 1. Create dummy models if not enough exist
    print("\n1. Checking/Creating models...")
    existing_labels = service.get_registered_labels()
    print(f"   Found {len(existing_labels)} existing models.")
    
    # Create valid face image (noise)
    dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Measure First Load (Cold Start)
    print("\n2. Measuring Cold Start (First Verify)...")
    start_time = time.time()
    # Force clear cache if possible or just rely on first run
    FaceService._models_cache = None 
    FaceService._last_cache_update = None
    
    service.verify_face(dummy_frame)
    cold_duration = time.time() - start_time
    print(f"   Cold Start Time: {cold_duration:.4f} seconds (Disk I/O + Processing)")
    
    # Measure Second Load (Cached)
    print("\n3. Measuring Warm Start (Cached Verify)...")
    start_time = time.time()
    service.verify_face(dummy_frame)
    warm_duration = time.time() - start_time
    print(f"   Warm Start Time: {warm_duration:.4f} seconds (Memory Cache)")
    
    # Calculate Improvement
    if warm_duration > 0:
        improvement = cold_duration / warm_duration
        print(f"\n✅ Speed Improvement: {improvement:.1f}x faster")
    else:
        print("\n✅ Speed Improvement: Infinite (Warm start took 0s)")
        
    print("\nTest Complete.")

if __name__ == "__main__":
    test_performance()
