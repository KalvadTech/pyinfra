#!/bin/sh

BRANCH_NAME=`git rev-parse --abbrev-ref HEAD`

case "${BRANCH_NAME}" in
    "next")
        DOCS_VERSION="next"
        ;;
    "current")
        DOCS_VERSION="latest"
        ;;
    "2.x")
        DOCS_VERSION="2.x"
        ;;
    "1.x")
        DOCS_VERSION="1.x"
        ;;
    "0.x")
        DOCS_VERSION="0.x"
        ;;
esac

if [ -z "${DOCS_VERSION}" ]; then
    echo "No docs version for this branch, noop!"
else
    echo "Building docs branch=${BRANCH_NAME}, version=${DOCS_VERSION}"
    env DOCS_VERSION=$DOCS_VERSION sphinx-build -a docs/ docs/public/en/$DOCS_VERSION/
fi
