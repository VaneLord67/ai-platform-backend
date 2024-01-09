from datetime import timedelta

from common.util import create_redis_client

if __name__ == '__main__':
    # 测试代码：向redis中设置停止信号，用于关闭摄像头
    stopSignalKey = "test_stop"
    client = create_redis_client()
    client.set(stopSignalKey, "1", ex=timedelta(hours=1))
