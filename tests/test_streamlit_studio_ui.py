import os
import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.autodq_web.persistence import repository_for_url
from app.autodq_web.project_store import project_service, project_service_for


ROOT = Path(__file__).resolve().parents[1]


class StreamlitStudioUITests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.previous_environment = {
            key: os.environ.get(key)
            for key in ("AUTODQ_AUTH_MODE", "AUTODQ_STUDIO_HOME", "MPLCONFIGDIR")
        }
        os.environ["AUTODQ_AUTH_MODE"] = "development"
        os.environ["AUTODQ_STUDIO_HOME"] = self.temporary_directory.name
        os.environ["MPLCONFIGDIR"] = str(
            Path(self.temporary_directory.name) / "matplotlib"
        )

    def tearDown(self):
        try:
            project_service().repository.engine.dispose()
        except Exception:
            pass
        project_service_for.cache_clear()
        repository_for_url.cache_clear()
        for key, value in self.previous_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temporary_directory.cleanup()

    @staticmethod
    def _selectbox(app: AppTest, label: str):
        return next(item for item in app.selectbox if item.label == label)

    @staticmethod
    def _button(app: AppTest, label: str):
        return next(item for item in app.button if item.label == label)

    def test_sample_project_survives_a_fresh_browser_session(self):
        app_path = ROOT / "app" / "streamlit_app.py"
        first = AppTest.from_file(app_path, default_timeout=60).run()
        self.assertEqual(list(first.exception), [])

        self._button(first, "Use sample sales data").click()
        first.run(timeout=60)
        self.assertEqual(list(first.exception), [])
        self.assertEqual(
            self._selectbox(first, "Project").value,
            "Sample sales analysis",
        )
        self.assertEqual(self._selectbox(first, "Dataset").value, "sales")
        self.assertEqual(first.metric[0].value, "5,035")

        reopened = AppTest.from_file(app_path, default_timeout=60).run()
        self._selectbox(reopened, "Project").select("Sample sales analysis")
        reopened.run(timeout=60)

        self.assertEqual(list(reopened.exception), [])
        self.assertEqual(self._selectbox(reopened, "Dataset").value, "sales")
        self.assertEqual(reopened.metric[0].value, "5,035")


if __name__ == "__main__":
    unittest.main()
