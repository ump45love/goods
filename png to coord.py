import cv2
import numpy as np

# PNG 이미지 읽기 (알파 채널 포함)
img = cv2.imread('q.png', cv2.IMREAD_UNCHANGED)

# 알파 채널 추출
alpha = img[:, :, 3]

# 컨투어 찾기
contours, hierarchy = cv2.findContours(alpha, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

# 제일 큰 컨투어 찾기
areas = [cv2.contourArea(c) for c in contours]
max_idx = np.argmax(areas)

# 출력용 복사본 (BGRA 이미지)
result = img.copy()

# 제일 큰 컨투어 제외한 나머지 컨투어 내부를 흰색으로 채우기
for i, cnt in enumerate(contours):
    if i != max_idx:
        # 내부를 흰색 (255,255,255,255)로 채움
        cv2.drawContours(result, [cnt], -1, (255, 255, 255, 255), thickness=cv2.FILLED)

# 결과 저장
cv2.imwrite('q.png', result)