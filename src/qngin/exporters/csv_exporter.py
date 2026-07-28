"""Stream rows as CSV chunks."""

from __future__ import annotations

import csv
import io


class CSVExporter:
    def export(self, rows, options: dict | None = None):
        def gen():
            writer = None
            buf = io.StringIO()
            for row in rows:
                if writer is None:
                    writer = csv.DictWriter(buf, fieldnames=list(row.keys()))
                    writer.writeheader()
                    yield buf.getvalue()
                    buf.seek(0)
                    buf.truncate(0)
                writer.writerow(row)
                yield buf.getvalue()
                buf.seek(0)
                buf.truncate(0)

        return gen()
