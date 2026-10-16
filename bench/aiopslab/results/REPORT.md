# AIOpsLab results

Model: qwen2.5:1.5b-16k

| Problem | aiopsone | baseline |
|---|---|---|
| misconfig_app_hotel_res-analysis-1 | fail (282 s) | fail (250 s) |
| misconfig_app_hotel_res-detection-1 | pass (150 s) | fail (144 s) |
| misconfig_app_hotel_res-localization-1 | fail (240 s) | fail (2758 s) |
| misconfig_app_hotel_res-mitigation-1 | pass (162 s) | fail (2595 s) |
| noop_detection_hotel_reservation-1 | pass (86 s) | pass (217 s) |
| revoke_auth_mongodb-analysis-1 | pass (90 s) | fail (149 s) |
| revoke_auth_mongodb-detection-1 | pass (147 s) | fail (147 s) |
| revoke_auth_mongodb-localization-1 | pass (151 s) | error (2960 s) |
| revoke_auth_mongodb-mitigation-1 | fail (270 s) | error (2962 s) |
| user_unregistered_mongodb-analysis-1 | fail (144 s) | fail (141 s) |
| user_unregistered_mongodb-detection-1 | pass (84 s) | fail (145 s) |
| user_unregistered_mongodb-localization-1 | pass (140 s) | fail (5913 s) |
| user_unregistered_mongodb-mitigation-1 | fail (266 s) | error (2887 s) |

| Agent | detection | localization | analysis | mitigation | total |
|---|---|---|---|---|---|
| aiopsone | 4/4 | 2/3 | 1/3 | 1/3 | 8/13 |
| baseline | 1/4 | 0/3 | 0/3 | 0/3 | 1/13 |
