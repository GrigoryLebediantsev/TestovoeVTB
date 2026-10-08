import argparse

import uvicorn

from .app import DemoBankMode, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description='Локальный демо-банк')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--mode', type=DemoBankMode, choices=list(DemoBankMode), default=DemoBankMode.NORMAL)
    arguments = parser.parse_args()
    uvicorn.run(create_app(arguments.mode), host=arguments.host, port=arguments.port)


if __name__ == '__main__':
    main()
