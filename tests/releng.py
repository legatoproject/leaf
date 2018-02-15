from leaf.core import LeafConstants, LeafRepository, LeafArtifact
from pathlib import Path


class RepositoryUtils():

    EXTENSIONS = {
        "compress-tar": '.tar',
        "compress-xz": '.tar.xz',
        "compress-bz2": '.tar.bz2',
        "compress-gz": '.tar.gz'
    }

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
                    manifest = LeafArtifact(manifestFile)
                    if str(manifest.getIdentifier()) != packageFolder.name:
                        raise ValueError(
                            "Naming error: " + str(manifest.getIdentifier()) + " != " + packageFolder.name)
                    extension = RepositoryUtils.EXTENSIONS.get(
                        manifest.getName(),  ".tar.xz")
                    outputFile = outputFolder / \
                        (str(manifest.getIdentifier()) + extension)
                    app.pack(manifestFile, outputFile)
                    if manifest.getName().startswith("composite"):
                        artifactsListComposite.append(outputFile)
                    else:
                        artifactsList.append(outputFile)

        app.index(outputFolder / "composite.json",
                  artifactsListComposite, "composite")

        app.index(outputFolder / "index.json",
                  artifactsList, "composite", composites=["composite.json"])


if __name__ == "__main__":
    # unittest.main()
    RepositoryUtils.generateRepo(Path("/home/seb/dev/leaf/leaf/tests/resources2"),
                                 Path("/home/seb/dev/leaf/leaf/tests/resources2-out"))
