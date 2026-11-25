class EngineRegistry:

    def __init__(self):
        self._engines = {}

    def register(self, name, engine):
        self._engines[name] = engine

    def get(self, name):
        if name not in self._engines:
            raise ValueError(
                f"Engine not registered: {name}"
            )

        return self._engines[name]

    def list_engines(self):
        return list(self._engines.keys())


engine_registry = EngineRegistry()