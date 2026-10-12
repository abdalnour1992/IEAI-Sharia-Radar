import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec("streamlit"),"Streamlit UI tests run in GitHub CI")
class Application(unittest.TestCase):
    def test_no_data_means_no_fake_metrics_and_disabled_run(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file("app.py",default_timeout=30).run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.metric),0)
        self.assertTrue(app.button[0].disabled)

    def test_all_languages_render_without_exception(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file("app.py",default_timeout=30).run()
        for language in ("ar","en","tr"):
            app.selectbox(key="language").set_value(language).run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(len(app.title),1)

    def test_invalid_protocol_is_explained_instead_of_synthetic_fallback(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file("app.py",default_timeout=30).run()
        self.assertEqual(len(app.exception),0)
        self.assertGreater(len(app.info),0)
        self.assertEqual(len(app.dataframe),0)


if __name__ == "__main__": unittest.main()
