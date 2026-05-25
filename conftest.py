import sys
import os

# Ensure project root is in sys.path so "from backend.xxx" imports work in tests
sys.path.insert(0, os.path.dirname(__file__))
