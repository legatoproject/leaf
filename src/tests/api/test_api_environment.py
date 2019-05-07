"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf.model.environment import Environment, IEnvProvider
from tests.testutils import LeafTestCase


class TestApiEnvironment(LeafTestCase):
    def test_simple(self):
        env = Environment("my env", content=[("A", "a"), ("B", "b")], in_files=["/tmp/a.in", "/tmp/b.in"], out_files=["/tmp/a.out", "/tmp/b.out"])

        with self.assertStdout(template_out="activate.out"):
            env.activate(
                comment_consumer=lambda l: print(Environment.tostring_comment(l)),
                kv_consumer=lambda k, v: print(Environment.tostring_export(k, v)),
                file_consumer=lambda f: print(Environment.tostring_file(f)),
            )
        with self.assertStdout(template_out="deactivate.out"):
            env.deactivate(
                comment_consumer=lambda l: print(Environment.tostring_comment(l)),
                kv_consumer=lambda k, v: print(Environment.tostring_export(k, v)),
                file_consumer=lambda f: print(Environment.tostring_file(f)),
            )

        env.generate_scripts(activate_file=self.volatile_folder / "activate.sh", deactivate_file=self.volatile_folder / "deactivate.sh")
        self.assertFileContentEquals(self.volatile_folder / "activate.sh", "activate.out")
        self.assertFileContentEquals(self.volatile_folder / "deactivate.sh", "deactivate.out")

    def test_multiple(self):
        env = Environment("my env 1", content=[("A1", "a1"), ("B1", "b1")], in_files=["/tmp/a1.in", "/tmp/b1.in"], out_files=["/tmp/a1.out", "/tmp/b1.out"])
        env.append(
            Environment("my env 2", content=[("A2", "a2"), ("B2", "b2")], in_files=["/tmp/a2.in", "/tmp/b2.in"], out_files=["/tmp/a2.out", "/tmp/b2.out"])
        )
        env.append(Environment("my env 3", in_files=["/tmp/a3.in", "/tmp/b3.in"], out_files=["/tmp/a3.out", "/tmp/b3.out"]))
        env.append(Environment("my env 4", content=[("A4", "a4"), ("B4", "b4")], in_files=["/tmp/a4.in", "/tmp/b4.in"]))
        env.append(Environment("my env 5", content=[("A5", "a5"), ("B5", "b5")], out_files=["/tmp/a5.out", "/tmp/b5.out"]))
        env.append(Environment("my env 6"))

        with self.assertStdout(template_out="activate.out"):
            env.activate(
                comment_consumer=lambda l: print(Environment.tostring_comment(l)),
                kv_consumer=lambda k, v: print(Environment.tostring_export(k, v)),
                file_consumer=lambda f: print(Environment.tostring_file(f)),
            )
        with self.assertStdout(template_out="deactivate.out"):
            env.deactivate(
                comment_consumer=lambda l: print(Environment.tostring_comment(l)),
                kv_consumer=lambda k, v: print(Environment.tostring_export(k, v)),
                file_consumer=lambda f: print(Environment.tostring_file(f)),
            )

        env.generate_scripts(activate_file=self.volatile_folder / "activate.sh", deactivate_file=self.volatile_folder / "deactivate.sh")
        self.assertFileContentEquals(self.volatile_folder / "activate.sh", "activate.out")
        self.assertFileContentEquals(self.volatile_folder / "deactivate.sh", "deactivate.out")

    def test_envprovider(self):
        class MyEnvProvider(IEnvProvider):
            def _getenvmap(self):
                return {"AaaA": "a b c"}

            def _getenvinfiles(self):
                return ["/tmp/a.in", "/tmp/b.in"]

            def _getenvoutfiles(self):
                return ["/tmp/a.out", "/tmp/b.out"]

        env = Environment("my env 1", content=[("A1", "a1"), ("B1", "b1")], in_files=["/tmp/a1.in", "/tmp/b1.in"], out_files=["/tmp/a1.out", "/tmp/b1.out"])
        env.append(MyEnvProvider("My custom env").build_environment(vr=lambda x: x.upper()))

        with self.assertStdout(template_out="activate.out"):
            env.activate(
                comment_consumer=lambda l: print(Environment.tostring_comment(l)),
                kv_consumer=lambda k, v: print(Environment.tostring_export(k, v)),
                file_consumer=lambda f: print(Environment.tostring_file(f)),
            )
        with self.assertStdout(template_out="deactivate.out"):
            env.deactivate(
                comment_consumer=lambda l: print(Environment.tostring_comment(l)),
                kv_consumer=lambda k, v: print(Environment.tostring_export(k, v)),
                file_consumer=lambda f: print(Environment.tostring_file(f)),
            )

        env.generate_scripts(activate_file=self.volatile_folder / "activate.sh", deactivate_file=self.volatile_folder / "deactivate.sh")
        self.assertFileContentEquals(self.volatile_folder / "activate.sh", "activate.out")
        self.assertFileContentEquals(self.volatile_folder / "deactivate.sh", "deactivate.out")
