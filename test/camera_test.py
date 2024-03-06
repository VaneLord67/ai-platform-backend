import cv2


def decode_fourcc(cc):
    return "".join([chr((int(cc) >> 8 * i) & 0xFF) for i in range(4)])


if __name__ == '__main__':
    rtsp_url = "rtsp://"
    cap = cv2.VideoCapture(rtsp_url)
    # 检查是否成功打开流
    if not cap.isOpened():
        print("Error: Failed to open RTSP stream.")
        exit()
    codec_info = cap.get(cv2.CAP_PROP_FOURCC)
    print(f'codec_info = {decode_fourcc(codec_info)}')
    # 循环读取并显示视频帧
    # while True:
    #     ret, frame = cap.read()
    #     if not ret:
    #         print("Error: Failed to receive frame.")
    #         break
    #     cv2.imshow('RTSP Stream', frame)
    #     # 检测键盘按键，如果按下 q 键则退出循环
    #     if cv2.waitKey(1) & 0xFF == ord('q'):
    #         break
    cap.release()
    cv2.destroyAllWindows()
