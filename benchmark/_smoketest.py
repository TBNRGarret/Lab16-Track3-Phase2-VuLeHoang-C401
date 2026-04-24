"""Quick smoke test: conflict update flow (rubric-mandated)."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from agent import MemoryAgent

a = MemoryAgent()
a.reset_memories()

print("--- turn 1 ---")
r1 = a.chat("Tôi tên Linh, dị ứng sữa bò.")
print("RESP:", r1["response"])
print("PROFILE:", a.profile.all())

print("--- turn 2 (correction) ---")
r2 = a.chat("À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.")
print("RESP:", r2["response"])
print("PROFILE:", a.profile.all())

print("--- turn 3 (recall) ---")
r3 = a.chat("Tôi dị ứng gì nhỉ?")
print("RESP:", r3["response"])
print("PROFILE:", a.profile.all())
