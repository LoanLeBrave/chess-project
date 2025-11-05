import cv2
import numpy as np
import os


orb = cv2.ORB_create(nfeatures=2000)  # plus de features !

img_test = cv2.imread("test3.jpg")  # ton image avec toutes les pièces
gray_test = cv2.cvtColor(img_test, cv2.COLOR_BGR2GRAY)

db_path = r"C:\Users\STROTZ Naela\chess-project\database"

db_images = [f for f in os.listdir(db_path) if f.endswith((".jpg"))]

bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

for db_img in db_images:
    path = os.path.join(db_path, db_img)
    img_db = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

    # Features
    kp1, des1 = orb.detectAndCompute(img_db, None)
    kp2, des2 = orb.detectAndCompute(gray_test, None)

    if des1 is None or des2 is None:
        continue

    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)

    # Garde les meilleurs
    good_matches = matches[:40]

    if len(good_matches) > 10:  # seuil minimal
        print(f"{db_img} -> {len(good_matches)} correspondances")

        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1,1,2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1,1,2)

        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC,5.0)
        if M is not None:
            h, w = img_db.shape
            pts = np.float32([[0,0],[0,h],[w,h],[w,0]]).reshape(-1,1,2)
            dst = cv2.perspectiveTransform(pts, M)

            img_test = cv2.polylines(img_test,[np.int32(dst)],True,(0,255,0),3)

cv2.imshow("Detection", img_test)
cv2.waitKey(0)
cv2.destroyAllWindows()
