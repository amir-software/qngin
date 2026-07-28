"""Pass-through exporter returning row dicts."""


class JsonExporter:
    def export(self, rows, options: dict | None = None):
        return list(rows)
