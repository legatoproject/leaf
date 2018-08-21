#!/bin/sh
set -e
set -u

# Check we're ready
if ! a2x --version; then
  echo "Missing system dependencies to build man pages; see README.md"
  exit 1
fi

__usage () {
	echo "Usage: $0 <ADOC_FOLDER> <MAN_FOLDER>"
}

if ! test $# -eq 2; then
  __usage
  exit 1
fi 

ADOC_FOLDER="$1"
OUTPUT_FOLDER="$2"
ROOT_FOLDER=$(dirname "$0")

echo "Generate manpages from files in $ADOC_FOLDER"
if ! test -d "$ADOC_FOLDER"; then
  echo "Invalid input folder: $ADOC_FOLDER"
  __usage
  exit 1
fi

echo "Manpage will be generated in $OUTPUT_FOLDER"
if ! test -d "$OUTPUT_FOLDER"; then
  mkdir -p "$OUTPUT_FOLDER"
fi

VERSION=$(git describe --tags)
echo "Using version: $VERSION"

# Remove previously generated manpages
rm -vf "$OUTPUT_FOLDER"/*.1

TMPPAGE=$(mktemp)
# Look for man pages
for PAGE in "$ADOC_FOLDER"/leaf*.adoc; do
	echo "Creating manpage from $PAGE in $OUTPUT_FOLDER"
  echo -n "" > "$TMPPAGE"
  if test -f "$ROOT_FOLDER/header.adoc"; then
    cat "$ROOT_FOLDER/header.adoc" >> "$TMPPAGE"
  fi
	cat "$PAGE" >> "$TMPPAGE"
	if test -f "$ROOT_FOLDER/footer.adoc"; then
    cat "$ROOT_FOLDER/footer.adoc" >> "$TMPPAGE"
  fi
	sed -e "s/{VERSION}/${VERSION}/" -i "$TMPPAGE"
	a2x -f manpage "$TMPPAGE" -D "$OUTPUT_FOLDER"
done
