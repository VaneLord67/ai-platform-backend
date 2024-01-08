from common.util import create_redis_client

if __name__ == '__main__':
    client = create_redis_client()
    result = client.type(name='206b3641-65eb-4fed-8613-aee1faaf80aa')
    print(type(result))
    print(result)

