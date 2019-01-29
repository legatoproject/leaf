"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import traceback

from tests.testutils import LeafTestCaseWithCli


class TestPluginGetsrc(LeafTestCaseWithCli):
    def __init__(self, *args, **kwargs):
        LeafTestCaseWithCli.__init__(self, *args, verbosity="verbose", **kwargs)

    @property
    def fake_src_file_tag(self):
        return self.ws_folder / "fake-test-src-tag"

    @property
    def fake_src_file_branch(self):
        return self.ws_folder / "fake-test-src-branch"

    def __disable(self, scope: str = None):
        if scope is not None:
            self.leaf_exec("getsrc", "test", "--disable", scope)
        else:
            self.leaf_exec("getsrc", "test", "--disable")
        self.assertFalse(self.fake_src_file_tag.is_file())
        self.assertFalse(self.fake_src_file_branch.is_file())
        self.check_profile_content("FEATURE-TEST", ["featured-with-source", "condition-A"])

    def __enable_then_disable(self, branch_expected: bool = False, scope: str = None):
        execargs = ["getsrc", "test"]
        if branch_expected:
            execargs += ["--source", "branch"]
        if scope is not None:
            execargs += [scope]
        self.leaf_exec(*execargs)
        self.assertEqual(not branch_expected, self.fake_src_file_tag.is_file())
        self.assertEqual(branch_expected, self.fake_src_file_branch.is_file())
        self.check_profile_content("FEATURE-TEST", ["featured-with-source", "source"])
        if branch_expected:
            self.fake_src_file_branch.unlink()
            self.assertFalse(self.fake_src_file_branch.is_file())
        else:
            self.fake_src_file_tag.unlink()
            self.assertFalse(self.fake_src_file_tag.is_file())
        self.__disable(scope=scope)

    def test_getsrc(self):
        try:
            # Setup profile without source features
            self.leaf_exec("setup", "FEATURE-TEST", "-p", "featured-with-source")
            self.check_current_profile("FEATURE-TEST")
            self.check_profile_content("FEATURE-TEST", ["featured-with-source", "condition-A"])

            # Verify source list + check unknown source module
            self.leaf_exec("getsrc")
            self.leaf_exec("getsrc", "unknown", expected_rc=2)
            self.assertFalse(self.fake_src_file_tag.is_file())
            self.assertFalse(self.fake_src_file_branch.is_file())

            # Trigger source mode for test
            self.__enable_then_disable()

            # Use alternative mode
            self.__enable_then_disable(branch_expected=True)

            # Scope: profile (explicit)
            self.__enable_then_disable(scope="--profile")

            # Scope: workspace
            self.__enable_then_disable(scope="--workspace")

            # Scope: workspace
            self.__enable_then_disable(scope="--user")
        except SystemExit:
            traceback.print_exc()
            self.fail("System exit caught")
