'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''


import os

from tests.testutils import LeafCliWrapper

from leaf import __version__


class TestCliEntrypoints(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testList(self):
        self.leafExec(("package", "install"), "scripts_1.0")

        with self.assertStdout(templateOut="list.out",
                               variables={}):
            self.leafExec("run")
        with self.assertStdout(templateOut="list-oneline.out",
                               variables={}):
            self.leafExec("run", "--oneline")

    def testRun(self):
        self.leafExec(("package", "install"), "scripts_1.0")
        self.leafExec("run", "env")
        self.leafExec("run", "echo", "hello", "world")

        def checkFileCreation(*args, rc=0):
            file = self.getWorkspaceFolder() / "myfile.test"
            self.assertFalse(file.exists())
            args = list(args)
            args.append(file)
            self.leafExec("run", *args, expectedRc=rc)
            if rc == 0:
                self.assertTrue(file.exists())
                file.unlink()
            else:
                self.assertFalse(file.exists())

        checkFileCreation('touch')
        checkFileCreation('mytouch', rc=2)
        checkFileCreation('-p', 'scripts_1.0', 'mytouch', rc=2)
        checkFileCreation('-p', 'subscripts_1.0', 'mytouch')
        checkFileCreation('--package', 'subscripts_1.0', 'mytouch')
        checkFileCreation('--package', 'subscripts_latest', 'mytouch')
        checkFileCreation('mytouch2')

    def testLatest(self):
        self.leafExec(("package", "install"),
                      "scripts_1.0", "subscripts_latest")

        file = self.getWorkspaceFolder() / "out.txt"

        def checkVersion(v):
            with file.open() as fp:
                self.assertEqual(["my special binary v%s\n" % v],
                                 fp.readlines())

        self.leafExec("run", "-p", "subscripts_1.0", "mybin", file)
        checkVersion("1.0")

        self.leafExec("run", "-p", "subscripts_1.1", "mybin", file)
        checkVersion("1.1")

        self.leafExec("run", "-p", "subscripts_latest", "mybin", file)
        checkVersion("1.1")

        self.leafExec("run", "-p", "scripts_1.0", "mybin", file)
        checkVersion("1.0")

        self.leafExec("run", "-p", "scripts_latest", "mybin", file)
        checkVersion("1.0")

        self.leafExec("run", "mybin", file)
        checkVersion("1.1")

    def testVariables(self):
        self.leafExec(("package", "install"), "scripts_1.0")

        self.leafExec("run", "foo", expectedRc=42)

        file = self.getWorkspaceFolder() / "out.txt"
        self.leafExec("env", "user", "--set",
                      "MY_CUSTOM_VAR2=Hello")
        self.leafExec("env", "user", "--set",
                      "MY_CUSTOM_VAR3=$MY_CUSTOM_VAR2 World")

        variables = {'LEAF_VERSION': __version__,
                     'LANG': os.getenv('LANG'),
                     'file': str(file)}

        def checkFileContent(lines):
            with file.open() as fp:
                self.assertListEqual(
                    list(map(lambda l: l.format(**variables) + '\n', lines)),
                    fp.readlines())

        fooShell = [
            'Test LANG={LANG}',
            'Test LEAF_VERSION={LEAF_VERSION}',
            'Test MY_CUSTOM_VAR1=My value',
            'Test MY_CUSTOM_VAR2=Hello',
            'Test MY_CUSTOM_VAR3=Hello World',
            'Arguments counts: 3',
            '  >{file}<',
            '  > hello world <',
            '  > {LEAF_VERSION} <']
        fooNoShell = [
            'Test LANG={LANG}',
            'Test LEAF_VERSION={LEAF_VERSION}',
            'Test MY_CUSTOM_VAR1=My value',
            'Test MY_CUSTOM_VAR2=Hello',
            'Test MY_CUSTOM_VAR3=$MY_CUSTOM_VAR2 World',
            'Arguments counts: 3',
            '  >{file}<',
            '  > hello world <',
            '  > $LEAF_VERSION <']
        fooShell2 = [
            'Test LANG={LANG}',
            'Test LEAF_VERSION={LEAF_VERSION}',
            'Test MY_CUSTOM_VAR1=My new value',
            'Test MY_CUSTOM_VAR2=Hello',
            'Test MY_CUSTOM_VAR3=Hello World',
            'Arguments counts: 3',
            '  >{file}<',
            '  > hello world <',
            '  > {LEAF_VERSION} <']

        tests = {
            ('foo', file, " hello world ", " $LEAF_VERSION "): fooShell,
            ('foo', '-p', 'scripts_1.0', file, " hello world ", " $LEAF_VERSION "): fooShell2,
            ('foo-noshell', file, " hello world ", " $LEAF_VERSION "): fooNoShell
        }
        for command, content in tests.items():
            if file.exists():
                file.unlink()
            self.assertFalse(file.exists())
            self.leafExec("run", *command)
            self.assertTrue(file.exists())
            checkFileContent(content)
