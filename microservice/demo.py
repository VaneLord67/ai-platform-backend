import eventlet
from nameko.events import event_handler, BROADCAST

eventlet.monkey_patch()

from nameko.cli.run import run
from nameko.rpc import rpc


class DemoService:
    name = "demo_service"

    @rpc
    def hello(self):
        return "hello!"

    @event_handler("manage_service", name + "close_event", handler_type=BROADCAST, reliable_delivery=False)
    def handle_event(self, payload):
        print("receive close event")
        raise KeyboardInterrupt


def run_service(service_cls):
    services = [service_cls]
    config = {
        "AMQP_URI": "pyamqp://guest:guest@localhost"
    }
    print(f"start service:{service_cls.name}")
    run(services, config)


if __name__ == '__main__':
    run_service(DemoService)

