# HMATES — Evaluation Report
> Generated: 2026-06-19 01:55

---

## 4. Pipeline Latency Benchmark

**Hardware:** Intel64 Family 6 Model 183 Stepping 1, GenuineIntel  
**CUDA:** Yes — NVIDIA GeForce RTX 3050  

| Stage            | Mean    | Min     | P95     |
| ---------------- | ------- | ------- | ------- |
| 01 preprocess    | 28.0 ms | 27.5 ms | 29.0 ms |
| 02 scene detect  | 10.1 ms | 9.6 ms  | 10.8 ms |
| 03 signal agent  | 20.3 ms | 18.5 ms | 22.6 ms |
| 04 parking agent | 9.6 ms  | 9.5 ms  | 9.7 ms  |
| 05 end to end    | 68.2 ms | 66.3 ms | 71.0 ms |

**Estimated FPS: ~14.7**

## 5. End-to-End Violation Classification Accuracy

**Overall: 0/0 = 0.0%**


---
## Summary

| Metric | Value |
|--------|-------|
| End-to-end accuracy | **0.0%** |
| Estimated FPS       | **~14.7** |

> *Emergency vehicles (AMBU/FIRE/POLICE/ARMY) are excluded from all evaluation.*
> *Evaluation conducted on labelled test images not used during training.*