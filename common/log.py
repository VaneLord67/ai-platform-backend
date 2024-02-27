import logging

# 1.创建一个logger实例，设置logger实例的名称，设定严重级别
LOGGER = logging.getLogger('ai logger')
LOGGER.setLevel(logging.DEBUG)
# 2.创建一个handler，这个主要用于控制台输出日志，并且设定严重级别
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# 3.创建handler的输出格式(formatter)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
# 4.将formatter添加到handler中
ch.setFormatter(formatter)
# 5.将handler添加到logger中LOGGER.addHandler(ch)
if not LOGGER.hasHandlers():
    LOGGER.addHandler(ch)

