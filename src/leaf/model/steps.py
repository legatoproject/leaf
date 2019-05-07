import re

from leaf.core.constants import JsonConstants
from leaf.core.error import LeafException
from leaf.core.logger import TextLogger
from leaf.model.environment import Environment
from leaf.model.modelutils import execute_command, find_manifest
from leaf.model.package import InstalledPackage, PackageIdentifier


class VariableResolver:

    _PATTERN = "@{{(NAME|VERSION|DIR)(?::(({name}){separator}({version})))?}}".format(
        name=PackageIdentifier.NAME_PATTERN, separator=PackageIdentifier.SEPARATOR, version=PackageIdentifier.VERSION_PATTERN
    )

    def __init__(self, current_package: InstalledPackage = None, other_packages: list = None):
        self.__current_package = current_package
        self.__all_packages = {}

        if other_packages is not None:
            for pkg in other_packages:
                self.__all_packages[pkg.identifier] = pkg
        if current_package is not None:
            self.__all_packages[current_package.identifier] = current_package

    def get_value(self, var: str, pis: str):
        pkg = None
        if pis is None:
            # No PI specified means current package
            pkg = self.__current_package
        else:
            pkg = find_manifest(PackageIdentifier.parse(pis), self.__all_packages, ignore_unknown=True)
        if pkg is not None:
            if var == "NAME":
                return pkg.name
            if var == "VERSION":
                return pkg.version
            if var == "DIR":
                return str(pkg.folder)

    def resolve(self, value: str):
        def myreplace(m):
            out = self.get_value(m.group(1), m.group(2))
            if out is None:
                raise LeafException("Cannot resolve variable: {var}".format(var=m.group(0)))
            return out

        return re.sub(VariableResolver._PATTERN, myreplace, value)


class StepExecutor:

    """
    Used to execute post install & pre uninstall steps
    """

    def __init__(self, logger: TextLogger, package: InstalledPackage, vr: VariableResolver, env=None):
        self.__logger = logger
        self.__package = package
        self.__env = env
        self.__target_folder = package.folder
        self.__vr = vr

    def install(self):
        self.__run_steps(self.__package.jsonget(JsonConstants.INSTALL), label="install")

    def uninstall(self):
        self.__run_steps(self.__package.jsonget(JsonConstants.UNINSTALL), label="uninstall")

    def sync(self):
        self.__run_steps(self.__package.jsonget(JsonConstants.SYNC), label="sync")

    def __run_steps(self, steps, label):
        if steps is not None and len(steps) > 0:
            self.__logger.print_default("Run {label} steps for {ip.identifier}".format(label=label, ip=self.__package))
            for step in steps:
                if JsonConstants.STEP_LABEL in step:
                    self.__logger.print_default(step[JsonConstants.STEP_LABEL])
                self.__execute(step, label)

    def __execute(self, step, label):
        command = step[JsonConstants.STEP_EXEC_COMMAND]
        command = list(map(self.__vr.resolve, command))
        command_text = " ".join(command)
        self.__logger.print_verbose("Execute: {command}".format(command=command_text))

        env = Environment()
        env.append(self.__env)
        env.append(Environment(content=step.get(JsonConstants.STEP_EXEC_ENV)))

        verbose = step.get(JsonConstants.STEP_EXEC_VERBOSE, False)

        rc = execute_command(*command, cwd=self.__target_folder, env=env, print_stdout=verbose or self.__logger.isverbose())
        if rc != 0:
            self.__logger.print_verbose("Command '{command}' exited with {rc}".format(command=command_text, rc=rc))
            if step.get(JsonConstants.STEP_IGNORE_FAIL, False):
                self.__logger.print_verbose("Step ignores failure")
            else:
                raise LeafException("Error during {label} step for {ip.identifier} (command returned {rc})".format(label=label, ip=self.__package, rc=rc))
