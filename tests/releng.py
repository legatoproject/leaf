from leaf.core import LeafConstants, LeafRepository, Manifest
import subprocess


class RepositoryUtils():

    FILENAMES = {
        "compress-tar_1.0": 'compress-tar_1.0.tar',
        "compress-xz_1.0":  'compress-xz_1.0.tar.xz',
        "compress-bz2_1.0": 'compress-bz2_1.0.tar.bz2',
        "compress-gz_1.0":  'compress-gz_1.0.tar.gz'
    }

    @staticmethod
    def checkMime(file, expectedMime):
        mime = subprocess.getoutput("file -bi " + str(file))
        if not mime.startswith("application/" + expectedMime):
            raise ValueError("Invalid mime: " + file + ": " + mime)

    @staticmethod
    def checkArchiveFormat(file):
        if (file.endswith(".tar")):
            RepositoryUtils.checkMime(file, "x-tar")
        elif (file.endswith(".tar.gz")):
            RepositoryUtils.checkMime(file, "gzip")
        elif (file.endswith(".tar.bz2")):
            RepositoryUtils.checkMime(file, "x-bzip2")
        elif (file.endswith(".tar.xz")):
            RepositoryUtils.checkMime(file, "x-xz")

    @staticmethod
    def generateRepo(sourceFolder, outputFolder, logger):
        outputFolder.mkdir(parents=True, exist_ok=True)
        artifactsList = []
        artifactsListComposite = []

        app = LeafRepository(logger)
        for packageFolder in sourceFolder.iterdir():
            if packageFolder.is_dir():
                manifestFile = packageFolder / LeafConstants.MANIFEST
                if manifestFile.is_file():
                    manifest = Manifest.parse(manifestFile)
                    if str(manifest.getIdentifier()) != packageFolder.name:
                        raise ValueError(
                            "Naming error: " + str(manifest.getIdentifier()) + " != " + packageFolder.name)
                    filename = RepositoryUtils.FILENAMES.get(str(manifest.getIdentifier()),
                                                             str(manifest.getIdentifier()) + ".leaf")
                    outputFile = outputFolder / filename
                    app.pack(manifestFile, outputFile)
                    RepositoryUtils.checkArchiveFormat(str(outputFile))
                    if manifest.getName().startswith("composite"):
                        artifactsListComposite.append(outputFile)
                    else:
                        artifactsList.append(outputFile)

        app.index(outputFolder / "composite.json",
                  artifactsListComposite, "composite")

        app.index(outputFolder / "index.json",
                  artifactsList, "composite", composites=["composite.json"])
