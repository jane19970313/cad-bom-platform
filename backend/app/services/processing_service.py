from app.engines.registry import engine_registry


class ProcessingService:

    def execute(
        self,
        engine_name: str,
        input_data: dict
    ):

        engine = engine_registry.get(engine_name)

        result = engine.process(input_data)

        return result