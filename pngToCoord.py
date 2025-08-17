import cv2
import numpy as np

# PNG 불러오기 (알파 채널 포함)
image = cv2.imread('q.png', cv2.IMREAD_UNCHANGED)

# 알파 채널만 추출 (투명도)
alpha = image[:, :, 3]

# 임계값 처리: 불투명한 부분만 마스크
_, mask = cv2.threshold(alpha, 1, 255, cv2.THRESH_BINARY)

# 윤곽선 찾기
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# (옵션) 좌표 정규화
height, width = alpha.shape
contour = contours[0]  # 가장 큰 외곽선만 사용
points = [(pt[0][0] / width, pt[0][1] / height) for pt in contour]

# 좌표 저장
with open("contour_coords.txt", "w") as f:
    for x, y in points:
        f.write(f"{x} {1 - y}\n")  # Blender의 Y축 뒤집힘 고려