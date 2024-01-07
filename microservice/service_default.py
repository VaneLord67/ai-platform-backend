from datetime import timedelta


def default_state_change_handler(unique_id, payload, state_lock, serviceInfo, new_state):
    if unique_id == payload:
        state_lock.acquire()
        serviceInfo.state = new_state
        state_lock.release()


def default_close_event_handler():
    print("receive close event")
    raise KeyboardInterrupt


def default_close_one_event_handler(payload, redis_client):
    print("receive close one event")
    close_unique_id = payload
    print(f"close_unique_id = {close_unique_id}")
    lock_ok = redis_client.set(close_unique_id, "locked", ex=timedelta(minutes=1), nx=True)
    if lock_ok:
        print("get close lock, raise KeyboardInterrupt...")
        raise KeyboardInterrupt
    else:
        print("close lock failed, continue running...")


def default_state_report_handler(payload, state_lock, service_info, redis_client):
    redis_list_key = payload
    state_lock.acquire()
    try:
        state_string = service_info.__str__()
        redis_client.rpush(redis_list_key, state_string)
    finally:
        state_lock.release()
