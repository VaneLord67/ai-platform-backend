import pytest
from nameko.standalone.rpc import ClusterRpcProxy

config = {
    "AMQP_URI": "pyamqp://guest:guest@localhost"
}


def ai_call_wrapper():
    with ClusterRpcProxy(config) as cluster_rpc:
        args: dict = {
            "hyperparameter": {},
            "supportInput": {
                "type": "single_picture_url",
                "value": "http://localhost:9000/ai-platform/zidane.jpg"
            }
        }
        cluster_rpc.detection_service.call(args)


@pytest.mark.benchmark(group='ai')
def test_ai(benchmark):
    benchmark(ai_call_wrapper)


if __name__ == '__main__':
    print(ai_call_wrapper())
