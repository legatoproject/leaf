# Makefile used to build leaf deliverables

# Setup directories
OUTPUT:=$(PWD)/output
TARGET:=$(PWD)/target
SRC:=$(PWD)/src

#.SILENT:
.PHONY: ci docker-build docker-test clean test test-tox gpg deb install archive

all: deb 

ci: clean test-tox deb archive

docker-build:
	docker build -t "leaf-test:latest" docker/

docker-test:
	docker run --rm \
		--user 1000 \
		-v $(PWD):/src/leaf \
		leaf-test:latest \
		sh -c 'cp -a /src/leaf /tmp/leaf && cd /tmp/leaf && make gpg ci'

clean:
	rm -rf \
		$(SRC)/nosetests-*.xml \
		$(SRC)/.coverage $(SRC)/cover-*/ $(SRC)/coverage-*.xml \
		$(TARGET) \
		$(OUTPUT)

test:
	cd $(SRC) && python3 -m nose \
		--with-coverage --cover-erase --cover-package=leaf -cover-inclusive \
			--cover-xml --cover-xml-file=coverage-current.xml \
			--cover-html --cover-html-dir=cover-current \
		--with-xunit \
			--xunit-file=nosetests-current.xml

test-tox:
	cd $(SRC) && tox 

gpg:
	gpg --batch --gen-key $(PWD)/packaging/gpg-script

deb:
	$(PWD)/packaging/mkdeb.sh

install:
	sudo dpkg -i $(TARGET)/leaf_latest.deb

archive: 
	mkdir -p $(OUTPUT)
	cp -a \
		$(SRC)/nosetests-*.xml \
		$(SRC)/coverage-*.xml \
		$(SRC)/cover-* \
		$(TARGET)/* \
		$(OUTPUT)/

